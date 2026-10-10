"""The last stage: an agent enters the calculated bid in the tender portal, signs it and reads the receipt.

The calculator has fixed every number. `submit_bid` hands them to a model as a bid sheet and lets it drive whatever
bid form the portal has: where the form is, what each step wants, which notation a field takes, how a position is
left out and when the signing code has to be requested are all read from the pages. A second agent, on the webmail,
fetches that code when the first one asks for it. Nothing here knows a field name or the order of the steps.
"""
from __future__ import annotations

import asyncio
import json
import time
from decimal import Decimal

import sanity
from browser_env import Tab
from calculator import Bid
from preflight import Report, check as check_review
from worker import ACTIONS_HELP, Agent

WRAP_UP = 150  # seconds before the deadline at which entering stops and signing starts: the code takes a while
MAIL_BUDGET = 120  # seconds one request to the mailbox may take
CLERK_STEPS, COURIER_STEPS = 120, 25
# How often the final step is held back because the page does not show the bid (preflight "unproven"). The wait is
# bounded: a signed bid scores, an unsigned one does not.
UNPROVEN_REFUSALS = 2
# Entering a bid is reading a form and copying values: without the model's long reasoning a turn takes about half
# the time, and the reply's "thought" still leaves it room to check a conversion.
CLERK_THINKS, COURIER_THINKS = False, False

CLERK = """You are the bid clerk of a manufacturer's sales engineering team. Your colleagues have researched a
public tender and a calculator has priced it: the BID SHEET below is the final result. You work the tender portal
"{site}" at {url} in your own browser tab, and your whole job is to get exactly this bid into the portal's bid
form, sign it, submit it and read the confirmation. You do not research and you do not recalculate.

TASK BRIEF (background on what a valid submission is; the values to enter come from the bid sheet)
{brief}
END OF BRIEF

BIDDER
{bidder}

BID SHEET
{sheet}

Reading the bid sheet
- "decision" is "bid" or "no_bid". A no_bid has no positions and a total of zero: take the form's way of
  declining, and still sign and submit it.
- "positions" has one entry per tender position that is offered. Enter each under its own position number.
- "material" describes the offered product, for forms that make you pick or configure it: choose what equals
  these values.
- Amounts are net EUR, written here with a decimal point and without thousands separators. A field may expect
  another notation (a decimal comma, a unit, whole numbers for weeks and pieces): follow its hints, placeholder
  and error messages. Change the notation only, never the value.
- null means the value is not known: leave that field empty. 0 or 0.00 is a known zero: enter it.
- "omitted_positions" could not be priced. Never invent values for them: use the form's explicit way of leaving
  a position out, if it has one.

{actions}
One more action:
  {{"do": "ask_mail", "task": "<what you need and how to recognise it>"}}
      A colleague who has the bidder's mailbox open in another browser looks for it and answers. This is how you
      get the signing code (TAN) the portal sends by mail. Ask only after you have triggered the code in the
      portal, and pass on what you know about it (the tender reference, that you requested it just now, anything
      the portal displayed about it): the mailbox also holds older codes that no longer work.
  {{"do": "check_submission"}}
      Read the current review page and produce a no-model checklist of visible errors, unfilled required controls,
      tender reference, offered positions and total. Run this immediately before the irreversible final step.
      BLOCKER is something the page shows to be wrong. NOT SHOWN is something a review must show and this page
      does not: a page that does not show the bid proves nothing about what the portal holds.
  {{"do": "finalize", "id": 12}}
      Press the final submit/confirm control only after check_submission reported READY. Never use ordinary click for
      the irreversible final submit control.

How to work
- Start from the page you are on and find the bid form of tender {reference}. Log in again if the portal asks.
- A bid form asks, in an order of its own, for things like the bidder's details, bid or no bid, the positions,
  the commercial terms, declarations, a review and a signature. Read each page and give it what it asks for,
  from the bidder data and the bid sheet. Fill every field the sheet has a value for, optional ones included.
- Read the form's own instructions: when entries are saved, what going back does, which fields are required.
  Do the fields of a page in one reply, then the control that saves them or moves on.
- After each step look at the result. If the form reports an error or did not keep a value, correct that field
  before you move on.
- Declarations: read what each one says. Give the confirmations a valid bid needs; leave unticked, or untick,
  options that would alter the bid or have nothing to do with it.
- On the review page compare what the form lists with the bid sheet: reference, decision, every position, the
  discount and the total. Go back and correct differences while there is time.
- Signing: trigger the code in the portal, get it with ask_mail, enter it and submit. A submission is final.
  If the portal rejects a code, request a fresh one instead of trying the same again.
- On the final review page, call check_submission. If it is BLOCKED, correct the reported issue and check again.
  Use finalize for the final irreversible confirmation only after it reports READY.
- You are finished only when the portal confirms that the bid was received. Then finish with done and put the
  confirmation (its receipt number or code, else its wording) in "answer". If you cannot submit, finish with
  done without "answer" and say why in "summary".
- Watch the time. A bid that is entered but not submitted scores nothing; a submitted bid with positions left
  out keeps the points of the positions it holds. When the head of a turn says time is short, do as it says.
"""

COURIER = """You have the sales mailbox of a bidding company open in the webmail "{site}" at {url}, in your own
browser tab. A colleague is entering the company's bid for tender {reference} in the tender portal right now and
asks you for something from the mailbox, usually the one-time signing code (TAN) the portal has just mailed.

{actions}

How to work
- The request heads every turn, together with the answers you gave earlier in this run.
- Codes expire. The mailbox can hold older codes, codes for other tenders whose references look alike, and
  unrelated mail with similar subjects. The one that counts is the newest sent message that matches the request (never
  an unsent draft). Open the message itself and check its reference, sent status and time before you answer: a row in
  a list is not enough.
- A newly requested signing code arrives as new incoming mail in the inbox (not in archive or drafts). Unlock the
  inbox and reload if the new message is not visible yet.
- Log in again if the webmail asks.
- Finish with done and put ONLY the value asked for in "answer": a code exactly as written, nothing around it.
  If you cannot find it, finish with done without "answer" and say in "summary" what you saw instead.
"""


def _amount(value: Decimal | None) -> str | None:
    return None if value is None else f"{value:.2f}"


def bid_sheet(bid: Bid) -> dict:
    """The bid as the clerk gets it: the answer's fields with exact amounts as text, the positions left out, and per
    position the offered material's attributes for forms that have the bidder configure the product."""
    positions = []
    for line in bid.lines:
        material = line.material
        positions.append({
            "position": line.position, "material_number": line.material_number,
            "material": None if material is None else {
                "bore_mm": material.bore_mm, "stroke_mm": material.stroke_mm, "pressure_bar": material.pressure_bar,
                "mounting": material.mounting, "certification": material.certification},
            "quantity": line.quantity, "unit_price": _amount(line.unit_price),
            "lead_time_weeks": line.lead_time_weeks, "base_unit_price": _amount(line.base_unit_price),
            "surcharge_per_unit": _amount(line.surcharge_per_unit),
            "packaging_per_unit": _amount(line.packaging_per_unit), "rebate_total": _amount(line.rebate_total)})
    discount = Decimal(bid.discount_percent)
    return {"tender_reference": bid.tender_reference, "decision": bid.decision, "currency": "EUR",
            "discount_percent": int(discount) if discount == discount.to_integral_value() else float(discount),
            "positions": positions, "omitted_positions": list(bid.omitted), "total_net": _amount(bid.total_net)}


async def submit_bid(tender_tab: Tab, mail_tab: Tab | None, bid: Bid, context: dict, brief: str,
                     deadline: float) -> dict:
    """Have an agent enter, sign and submit `bid` in the tender portal before `deadline` (a time.time() value).

    `context` holds tender_reference, scenario_date, company, vat_id and email. Returns {"submitted", "receipt",
    "notes"}: `receipt` is the portal's confirmation as the agent read it, empty when there was none.
    """
    reference = str(context.get("tender_reference") or bid.tender_reference)
    guard = sanity.TypingGuard() if sanity.enabled("typing_guard") else None
    codes: list[str] = []  # what the mailbox handed out so far: a used code must not be handed out again
    review: Report | None = None
    held_back = 0  # final steps refused because the page did not show the bid

    # The courier gets a fresh tab in the mailbox's browser (same session), opened now in the background while the
    # bid form is filled: the investigators' tab can be left half-navigated by the deadline that stopped them, and
    # a cold mailbox costs minutes when the signing code is waiting (sandbox test run 54c78c38).
    courier_tab: Tab | None = None
    warming = None
    if mail_tab is not None:
        try:
            page = await mail_tab.page.context.new_page()
            courier_tab = Tab(page, {"siteId": mail_tab.site_id, "url": mail_tab.base_url,
                                     "credentials": mail_tab.credentials})
            warming = asyncio.ensure_future(courier_tab.goto(courier_tab.base_url + "/"))
        except Exception:  # noqa: BLE001  no second tab: fall back to the investigators' one
            courier_tab = mail_tab

    async def ask_mail(action: dict) -> str:
        task = str(action.get("task") or "").strip()
        if not task:
            return 'ask_mail needs a "task": say what you need from the mailbox and how to recognise it'
        if courier_tab is None:
            return "there is no mailbox in this run, so nothing can be fetched by mail"
        if warming is not None and not warming.done():
            try:
                await asyncio.wait_for(asyncio.shield(warming), 20)
            except Exception:  # noqa: BLE001  the courier opens the page itself then
                pass

        def request() -> str:
            text = f"REQUEST FROM YOUR COLLEAGUE AT THE TENDER PORTAL\n{task}"
            if codes:
                text += ("\n\nANSWERS YOU GAVE EARLIER IN THIS RUN (they are used up: a new request needs a newer "
                         "message)\n" + "\n".join(f"- {code}" for code in codes))
            return text

        system = COURIER.format(site=courier_tab.site_id, url=courier_tab.base_url, reference=reference,
                                actions=ACTIONS_HELP)
        courier = Agent("courier", courier_tab, system, request, deadline=min(deadline, time.time() + MAIL_BUDGET),
                        max_steps=COURIER_STEPS, think=COURIER_THINKS)
        outcome = await courier.run()
        answer = str(outcome.get("answer") or "").strip()
        if not answer:
            return "the mailbox colleague found nothing: " + (outcome.get("summary") or "no result in the time given")
        codes.append(answer)
        if guard is not None:
            guard.allow(answer)  # read from the mailbox during the run: the clerk may type it
        return f'the mailbox colleague answers: "{answer}"' + (f' ({outcome["summary"]})' if outcome.get("summary") else "")

    async def look() -> Report:
        report = check_review(await tender_tab.observe(), bid, reference)
        if report.unproven and not sanity.enabled("summary_check"):  # switched off: missing evidence only warns
            report = Report(not report.blockers, report.blockers, report.warnings + report.unproven, report.checks)
        return report

    async def check_submission(action: dict) -> str:
        nonlocal review
        review = await look()
        return review.text()

    async def finalize(action: dict) -> str:
        nonlocal review, held_back
        # Navigation, expiry and server validation can invalidate an earlier review, so inspect it again.
        review = await look()
        if review.blockers:
            return review.text() + "\nFinal submission was not pressed."
        if review.unproven:
            # The page does not show the bid, so pressing here would confirm something nobody compared. The clerk
            # is sent to a page that does show it, a bounded number of times and never when time is short.
            short = deadline - time.time() < WRAP_UP
            if held_back < UNPROVEN_REFUSALS and not short:
                held_back += 1
                return review.text() + "\nFinal submission was not pressed."
            print("[submit] final step pressed without full review evidence ("
                  + ("time is short" if short else f"held back {held_back} time(s)") + "): "
                  + " | ".join(review.unproven), flush=True)
        return await tender_tab.click(action.get("id"))

    def heading() -> str:
        left = int(deadline - time.time())
        text = f"YOUR JOB: enter, sign and submit the bid for tender {reference}, then read the confirmation."
        if codes:
            text += "\nCodes from the mailbox so far, oldest first: " + ", ".join(codes)
        if left < WRAP_UP:
            text += (f"\nTIME IS SHORT ({left} s). Enter no further positions: leave out the ones not entered yet if "
                     "the form allows it, go straight to the signature, fetch the code and submit what is entered.")
        return text

    bidder = {"company": context.get("company"), "vat_id": context.get("vat_id"), "email": context.get("email")}
    sheet = bid_sheet(bid)
    system = CLERK.format(site=tender_tab.site_id, url=tender_tab.base_url, brief=brief, reference=reference,
                          bidder=json.dumps(bidder, ensure_ascii=False, indent=1),
                          sheet=json.dumps(sheet, ensure_ascii=False, indent=1), actions=ACTIONS_HELP)
    if sanity.enabled("no_guessed_mailbox") and not bidder.get("email"):
        system += ("\nTHE BIDDER'S E-MAIL ADDRESS IS NOT KNOWN YET. If the form asks for it, get it with ask_mail (the "
                   "mailbox colleague can read the address of the mailbox it has open) and type exactly that. Never "
                   "make up an address, not even a plausible one.\n")
    if guard is not None:
        guard.allow(sheet)
        guard.allow(bidder)
        guard.allow(reference)
    clerk = Agent("submit", tender_tab, system, heading,
                  extra={"ask_mail": ask_mail, "check_submission": check_submission, "finalize": finalize}, deadline=deadline,
                  max_steps=CLERK_STEPS, think=CLERK_THINKS, guard=guard)
    outcome = await clerk.run()
    receipt = str(outcome.get("answer") or "").strip()
    notes = str(outcome.get("summary") or "")
    if not outcome.get("done"):
        notes = (notes + " " if notes else "") + f"stopped after {outcome.get('steps', 0)} steps without a confirmation"
    return {"submitted": bool(outcome.get("done") and receipt), "receipt": receipt, "notes": notes}

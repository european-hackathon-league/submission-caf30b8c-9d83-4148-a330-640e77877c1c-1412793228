"""Entering the bid: a model-directed agent fills the tender portal's bid form, a second one reads the signing TAN.

The calculator has already worked out every number; this module only hands them to the agents, written the way a
German form expects them. Where the form is, which bid type and which fields to choose, what to tick and when to
sign are the submitting agent's calls, guided by the brief's submission instructions. When it asks for the TAN, a
mail agent finds the newest signing message for this tender in the bidder's webmail and reads the code from it.
"""
from __future__ import annotations

import time
from decimal import Decimal

from browser_env import Tab
from calculator import Bid
from worker import ACTIONS_HELP, Agent

SUBMITTER = """You are the agent that enters a finished tender bid in the tender portal "{site}" at {url} and submits
it. The numbers are final: they were worked out from the evidence and you must not change, recalculate or round them.
Type every amount exactly as given below (German number format, comma before the cents).

TASK BRIEF (its submission instructions are authoritative)
{brief}
END OF BRIEF

{actions}
Extra action:
  {{"do": "get_tan", "note": "<what the portal said about the TAN>"}}
      Has a colleague read the newest signing TAN for this tender from the bidder's webmail and returns it. Use it
      only after the portal has sent a TAN (after you requested it), and enter the code right away: a TAN expires
      after a few minutes and a new request makes the previous one invalid, so request it only once, as the last
      step before signing.

How to work
- Follow the brief's submission steps in order. Register the bidder exactly with the details given below.
- Choose the bid type that matches the decision: the main offer for a bid, the declaration of non-participation for
  a no bid. Never leave a default offer type in place without checking it.
- Enter one line per position below, matched by its position number, with its material, quantity, unit price, lead
  time and the breakdown fields. Positions listed as omitted are left out with the form's own omit option.
- Leave everything not named in the brief or below at its neutral setting: do not add positions, do not tick terms
  of your own or optional extras. Acknowledge the tender documents when the form asks.
- The form may show a gross amount including VAT: it is not the net total. Check that the net total shown matches.
- Going back can clear later steps, and an expired session loses unsaved entries: move forward step by step, and
  after logging in again check what the form still holds.
- Submitting is final and allowed once. Before the final confirmation, read the summary and compare it with the
  values below. When the portal confirms the submission, finish with done and put the confirmation text in answer.
"""

TAN_READER = """You read the bidder's webmail "{site}" at {url} to find one signing TAN.

{actions}
Your job: a signing TAN (Transaktionsnummer) for tender {reference} was requested moments ago. Open the newest
message that delivers it, read the TAN code in it and finish with {{"do": "done", "summary": "...", "answer": "<code>"}}.
Older TAN messages can exist, and their dates may all look the same (the mailbox runs on the scenario's clock): a
request or sequence number in the messages tells which one is newest; take the highest. The message may only arrive after a few seconds:
reload the inbox if it is not there yet. Look-alike tender references (with an extra suffix) are not this tender.
"""


def german(value: Decimal | None) -> str:
    """A money amount as a German form expects it: 12345.6 -> "12.345,60"."""
    if value is None:
        return "(leave empty)"
    whole, _, cents = f"{value:,.2f}".partition(".")
    return f"{whole.replace(',', '.')},{cents}"


def bid_sheet(bid: Bid, details: dict) -> str:
    rows = [f"Tender reference: {bid.tender_reference}",
            f"Decision: {'BID (main offer)' if bid.decision == 'bid' else 'NO BID (declaration of non-participation)'}",
            f"Bidder: {details.get('company')} · VAT id: {details.get('vat_id')} · e-mail: {details.get('email') or '(as the form needs)'}",
            f"Discount percent: {german(bid.discount_percent)}",
            f"Total net (EUR): {german(bid.total_net)}"]
    if bid.decision == "bid":
        rows.append("Positions:")
        for line in sorted(bid.lines, key=lambda line: line.position):
            rows.append(
                f"- {line.position}: material {line.material_number} · quantity {line.quantity} pieces · "
                f"unit price {german(line.unit_price)} · lead time {line.lead_time_weeks} weeks · "
                f"base unit price {german(line.base_unit_price)} · surcharge per unit {german(line.surcharge_per_unit)} · "
                f"packaging per unit {german(line.packaging_per_unit)} · rebate total {german(line.rebate_total)}")
        if bid.omitted:
            rows.append("Omitted positions (use the form's omit option): " + ", ".join(bid.omitted))
    return "\n".join(rows)


async def read_tan(mail_tab: Tab, reference: str, deadline: float) -> str:
    system = TAN_READER.format(site=mail_tab.site_id, url=mail_tab.base_url, actions=ACTIONS_HELP, reference=reference)
    reader = Agent(f"{mail_tab.site_id}:tan", mail_tab, system, lambda: f"Find the TAN for {reference}.",
                   deadline=min(deadline, time.time() + 150), max_steps=25, think=False)
    outcome = await reader.run()
    code = str(outcome.get("answer") or "").strip()
    return f"TAN: {code}" if code else f"no TAN found ({outcome.get('summary', '')[:200]})"


async def submit_bid(tender_tab: Tab, mail_tab: Tab | None, bid: Bid, details: dict, brief: str,
                     hard_stop: float) -> dict:
    sheet = bid_sheet(bid, details)
    system = SUBMITTER.format(site=tender_tab.site_id, url=tender_tab.base_url, brief=brief, actions=ACTIONS_HELP)

    async def get_tan(action: dict) -> str:
        if mail_tab is None:
            return "no webmail is available in this run"
        return await read_tan(mail_tab, bid.tender_reference, hard_stop)

    agent = Agent(f"{tender_tab.site_id}:submit", tender_tab, system,
                  lambda: "THE BID TO ENTER\n" + sheet, extra={"get_tan": get_tan},
                  deadline=hard_stop, max_steps=90)
    outcome = await agent.run()
    return {"submitted": bool(outcome.get("done")), "confirmation": outcome.get("answer"),
            "summary": outcome.get("summary"), "steps": outcome.get("steps")}

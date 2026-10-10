"""The bid-entry stage against a scripted model and fake tabs: what the clerk is told, how the signing code travels
from the mailbox agent to the clerk, and what `submit_bid` reports."""
import sys
import time
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import llm  # noqa: E402
import submit  # noqa: E402
from calculator import Bid, Line, Material  # noqa: E402

CONTEXT = {"tender_reference": "T-0001", "scenario_date": "2030-03-01T09:00:00+00:00", "company": "Example Works",
           "vat_id": "XX000000001", "email": "sales@bidder.example"}


def a_bid(**changes) -> Bid:
    material = Material(number="M-1", bore_mm=50, stroke_mm=200, pressure_bar=160, mounting="flange",
                        certification="none")
    priced = Line("1", "M-1", 40, unit_price=Decimal("12.50"), lead_time_weeks=3, base_unit_price=Decimal("12.00"),
                  surcharge_per_unit=Decimal("0.50"), packaging_per_unit=Decimal("0"), rebate_total=None,
                  material=material)
    bid = Bid("T-0001", "bid", Decimal("2.5"), [priced], Decimal("500.00"), omitted=["2"])
    for name, value in changes.items():
        setattr(bid, name, value)
    return bid


class FakeTab:
    """As much of a Tab as the agent loop touches; it records the actions it was given."""

    def __init__(self, site_id: str):
        self.site_id, self.base_url = site_id, f"http://{site_id}.test"
        self.page = SimpleNamespace(url=self.base_url + "/start", main_frame=self)
        self.document, self.document_source, self.done = "", "", []

    async def evaluate(self, script):
        return True

    async def observe(self) -> str:
        return f"url: {self.page.url}\ntitle: {self.site_id}\n[1] button \"go\""

    def take_events(self) -> list[str]:
        return []

    async def click(self, aid) -> str:
        self.done.append(("click", aid))
        return f"clicked [{aid}]"

    async def fill(self, aid, text, enter=False) -> str:
        self.done.append(("fill", aid, text))
        return f"filled [{aid}]"


class Script:
    """Stands in for llm.chat_json: answers each agent, named by `label`, with its next scripted reply."""

    def __init__(self, **replies):
        self.replies, self.asked = replies, []

    async def __call__(self, messages, *, think=True, max_tokens=6000, label=""):
        self.asked.append({"label": label, "think": think, "system": messages[0]["content"],
                           "user": messages[-1]["content"]})
        return self.replies[label].pop(0) if self.replies.get(label) else {}

    def turns(self, label: str) -> list[dict]:
        return [call for call in self.asked if call["label"] == label]


def done(**fields) -> dict:
    return {"thought": "", "actions": [{"do": "done", **fields}]}


class TheBidSheet(unittest.TestCase):
    def test_amounts_are_exact_text_and_unknown_values_stay_empty(self):
        sheet = submit.bid_sheet(a_bid())
        line = sheet["positions"][0]
        self.assertEqual((line["unit_price"], line["base_unit_price"], line["surcharge_per_unit"]),
                         ("12.50", "12.00", "0.50"))
        self.assertEqual(line["packaging_per_unit"], "0.00")  # a known zero is entered
        self.assertIsNone(line["rebate_total"])  # an unknown value is left blank
        self.assertEqual((line["quantity"], line["lead_time_weeks"]), (40, 3))
        self.assertEqual((sheet["total_net"], sheet["discount_percent"], sheet["omitted_positions"]),
                         ("500.00", 2.5, ["2"]))

    def test_each_position_carries_the_offered_materials_attributes(self):
        material = submit.bid_sheet(a_bid())["positions"][0]["material"]
        self.assertEqual(material, {"bore_mm": 50, "stroke_mm": 200, "pressure_bar": 160, "mounting": "flange",
                                    "certification": "none"})

    def test_a_no_bid_is_an_empty_sheet_with_a_whole_number_discount(self):
        sheet = submit.bid_sheet(a_bid(decision="no_bid", lines=[], omitted=[], total_net=Decimal("0"),
                                       discount_percent=Decimal("0")))
        self.assertEqual((sheet["decision"], sheet["positions"], sheet["total_net"], sheet["discount_percent"]),
                         ("no_bid", [], "0.00", 0))


class EnteringTheBid(unittest.IsolatedAsyncioTestCase):
    async def run_with(self, script: Script, mail_tab="mail", seconds: float = 900) -> tuple[dict, FakeTab]:
        tender = FakeTab("tender")
        mail = FakeTab("mail") if mail_tab else None
        with patch.object(llm, "chat_json", script):
            result = await submit.submit_bid(tender, mail, a_bid(), CONTEXT, "THE BRIEF", time.time() + seconds)
        return result, tender

    async def test_the_clerk_is_given_the_brief_the_bidder_and_the_sheet(self):
        script = Script(submit=[done(answer="R-1")])
        await self.run_with(script)
        first = script.turns("submit")[0]
        for expected in ("THE BRIEF", "Example Works", "XX000000001", "sales@bidder.example", '"unit_price": "12.50"',
                         '"omitted_positions"', "ask_mail", "http://tender.test"):
            self.assertIn(expected, first["system"])
        self.assertIn("tender T-0001", first["user"])
        self.assertNotIn("TIME IS SHORT", first["user"])

    async def test_the_signing_code_comes_from_an_agent_on_the_mailbox(self):
        script = Script(
            submit=[{"thought": "", "actions": [{"do": "ask_mail", "task": "the code I requested just now"}]},
                    {"thought": "", "actions": [{"do": "fill", "id": 1, "text": "CODE-7"}, {"do": "click", "id": 1}]},
                    done(answer="R-1", summary="received")],
            courier=[done(answer=" CODE-7 ")])
        result, tender = await self.run_with(script)
        courier = script.turns("courier")[0]
        self.assertIn("http://mail.test", courier["system"])
        self.assertIn("T-0001", courier["system"])
        self.assertIn("the code I requested just now", courier["user"])
        self.assertIn('the mailbox colleague answers: "CODE-7"', script.turns("submit")[1]["user"])
        self.assertIn(("fill", 1, "CODE-7"), tender.done)
        self.assertEqual(result, {"submitted": True, "receipt": "R-1", "notes": "received"})

    async def test_a_code_that_was_handed_out_is_not_handed_out_again(self):
        ask = {"thought": "", "actions": [{"do": "ask_mail", "task": "a fresh code"}]}
        script = Script(submit=[ask, ask, done(answer="R-1")], courier=[done(answer="CODE-1"), done(answer="CODE-2")])
        await self.run_with(script)
        first, second = script.turns("courier")
        self.assertNotIn("CODE-1", first["user"])
        self.assertIn("- CODE-1", second["user"])
        self.assertIn("Codes from the mailbox so far, oldest first: CODE-1, CODE-2", script.turns("submit")[2]["user"])

    async def test_the_clerk_hears_when_the_mailbox_has_nothing(self):
        ask = {"thought": "", "actions": [{"do": "ask_mail", "task": "the code"}]}
        script = Script(submit=[ask, done(summary="no code")], courier=[done(summary="no such message")])
        result, _ = await self.run_with(script)
        self.assertIn("the mailbox colleague found nothing: no such message", script.turns("submit")[1]["user"])
        self.assertEqual(result, {"submitted": False, "receipt": "", "notes": "no code"})

    async def test_without_a_mailbox_in_the_run_the_clerk_is_told_so(self):
        ask = {"thought": "", "actions": [{"do": "ask_mail", "task": "the code"}]}
        script = Script(submit=[ask, done(summary="cannot sign")])
        result, _ = await self.run_with(script, mail_tab=None)
        self.assertIn("there is no mailbox in this run", script.turns("submit")[1]["user"])
        self.assertEqual(script.turns("courier"), [])
        self.assertFalse(result["submitted"])

    async def test_a_bid_without_confirmation_is_not_reported_as_submitted(self):
        result, _ = await self.run_with(Script(submit=[]))  # the model never gives a usable reply
        self.assertFalse(result["submitted"])
        self.assertIn("without a confirmation", result["notes"])

    async def test_when_time_is_short_the_clerk_is_told_to_sign_and_submit(self):
        script = Script(submit=[done(answer="R-1")])
        await self.run_with(script, seconds=submit.WRAP_UP - 30)
        self.assertIn("TIME IS SHORT", script.turns("submit")[0]["user"])

    async def test_after_the_deadline_nothing_is_entered(self):
        script = Script(submit=[done(answer="R-1")])
        result, tender = await self.run_with(script, seconds=-1)
        self.assertEqual((script.asked, tender.done, result["submitted"]), ([], [], False))


if __name__ == "__main__":
    unittest.main()

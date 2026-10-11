"""fill_positions (submit.py): the clerk enters one position by hand, then hands its steps over as a template; code
enters every further position the form shows with that position's values from the bid sheet. Runs 15a3aaf9 and
49f7be51 spent 35-100 clerk turns on the positions and looped. Invented form and values only."""
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


def line(position, number, quantity, price, weeks):
    material = Material(number=number, bore_mm=50, stroke_mm=200, pressure_bar=160, mounting="flange",
                        certification="none")
    return Line(position, number, quantity, unit_price=Decimal(price), lead_time_weeks=weeks, base_unit_price=None,
                surcharge_per_unit=None, packaging_per_unit=None, rebate_total=None, material=material)


def three_positions() -> Bid:
    lines = [line("1", "M-1", 4, "10.50", 2), line("2", "M-2", 30, "1234.56", 6), line("3", "M-3", 7, "99.00", 1)]
    return Bid("T-0001", "bid", Decimal("0"), lines, Decimal("38099.80"), omitted=[])


TEMPLATE = [{"field": "Material", "value": "{material_number}"}, {"field": "Menge", "value": "{quantity}"},
            {"field": "Preis", "value": "{unit_price|de}"}, {"field": "Lieferzeit", "value": "{lead_time_weeks}"},
            {"press": "Weiter"}]


class PositionForm:
    """Shows one position at a time ("# Position <n>"); its element ids change on every page. "Weiter" takes the
    entered values when all are there and moves on, else it shows an error and stays."""

    def __init__(self, order=("1", "2", "3"), refuse=None):
        self.order, self.index, self.offset, self.refuse = list(order), 0, 0, refuse
        self.base_url, self.site_id = "http://form.test", "tender"
        self.page = SimpleNamespace(url=self.base_url + "/form", main_frame=SimpleNamespace(evaluate=self._alive))
        self.document, self.document_source, self.current, self.saved, self.error = "", "", {}, {}, ""

    async def _alive(self, script):
        return True

    def take_events(self):
        return []

    def ids(self):
        return {name: str(i + self.offset) for i, name in enumerate(("material", "qty", "price", "weeks", "next"))}

    async def observe(self):
        i = self.ids()
        if self.index >= len(self.order):
            view = 'url: http://form.test/form\n# Konditionen\n[90] input "Rabatt" value=""'
        else:
            view = "\n".join(["url: http://form.test/form", f"# Angebot - Position {self.order[self.index]}",
                              f'[{i["material"]}] select "Material" options: "M-1"; "M-2"; "M-3"',
                              f'[{i["qty"]}] input "Menge" value=""', f'[{i["price"]}] input "Preis" value=""',
                              f'[{i["weeks"]}] input "Lieferzeit" value=""', f'[{i["next"]}] button "Weiter"']
                             + ([f"(alert) {self.error}"] if self.error else []))
        self.document = view
        return view

    async def select(self, aid, value):
        self.current["material"] = value
        return f'selected "{value}"'

    async def fill(self, aid, text, enter=False):
        key = {v: k for k, v in self.ids().items()}.get(str(aid))
        self.current[key] = text
        return f"filled [{aid}]"

    async def click(self, aid):
        if str(aid) != self.ids()["next"]:
            return f"[{aid}] not found"
        position = self.order[self.index]
        if position == self.refuse or len(self.current) < 4:
            self.error, self.offset = "Bitte alle Felder ausfuellen", self.offset + 10
            return "clicked; the page reloaded"
        self.saved[position], self.current, self.error = dict(self.current), {}, ""
        self.index, self.offset = self.index + 1, self.offset + 10
        return "clicked; the page reloaded"


class Script:
    def __init__(self, replies):
        self.replies, self.seen = list(replies), []

    async def __call__(self, messages, *, think=True, max_tokens=6000, label=""):
        self.seen.append(messages[-1]["content"])
        return self.replies.pop(0) if self.replies else {"thought": "", "actions": [{"do": "done", "summary": "x"}]}


async def run(form, replies):
    script = Script(replies)
    with patch.object(llm, "chat_json", script):
        await submit.submit_bid(form, None, three_positions(), CONTEXT, "THE BRIEF", time.time() + 900)
    return script


def replay(done=("1",)):
    return {"thought": "position 1 is in; the others the same way",
            "actions": [{"do": "fill_positions", "done": list(done), "template": TEMPLATE}]}


class FillPositions(unittest.IsolatedAsyncioTestCase):
    async def test_every_further_position_is_entered_with_its_own_values(self):
        form = PositionForm()
        form.index = 1  # position 1 was entered by hand
        script = await run(form, [replay()])
        self.assertEqual(form.saved, {
            "2": {"material": "M-2", "qty": "30", "price": "1234,56", "weeks": "6"},
            "3": {"material": "M-3", "qty": "7", "price": "99,00", "weeks": "1"}})
        self.assertIn("no further bid position is shown", script.seen[1])

    async def test_the_form_order_decides_which_values_go_in(self):
        form = PositionForm(order=("1", "3", "2"))
        form.index = 1
        await run(form, [replay()])
        self.assertEqual(form.saved["3"]["material"], "M-3")
        self.assertEqual(form.saved["2"]["price"], "1234,56")

    async def test_a_position_the_form_does_not_accept_stops_the_replay(self):
        form = PositionForm(refuse="2")
        form.index = 1
        script = await run(form, [replay()])
        self.assertEqual(form.saved, {})
        self.assertIn("did not move on", script.seen[1])

    async def test_positions_entered_by_hand_are_never_entered_again(self):
        form = PositionForm()  # still shows position 1
        script = await run(form, [replay(done=("1",))])
        self.assertEqual(form.saved, {})
        self.assertIn("no further bid position is shown", script.seen[1])


class TheTemplate(unittest.TestCase):
    LINE = {"position": "2", "material_number": "M-2", "quantity": 30, "unit_price": "1234.56", "lead_time_weeks": 6,
            "rebate_total": None, "material": {"bore_mm": 50, "certification": None}}

    def test_placeholders_take_the_lines_values(self):
        steps = submit.fill_template([{"field": "Bore", "value": "{bore_mm}"},
                                      {"field": "Price", "value": "{unit_price|de}"}, {"press": "Next"}], self.LINE)
        self.assertEqual(steps, [{"field": "Bore", "value": "50"}, {"field": "Price", "value": "1234,56"},
                                 {"press": "Next"}])

    def test_a_null_value_leaves_its_field_out_unless_the_template_names_a_text(self):
        steps = submit.fill_template([{"field": "Rebate", "value": "{rebate_total}"},
                                      {"field": "Certificate", "value": "{certification|none=Without}"}], self.LINE)
        self.assertEqual(steps, [{"field": "Certificate", "value": "Without"}])

    def test_the_shown_position_is_read_from_the_heading(self):
        page = 'Positions: 1, 2, 3\n# Offer - Position 3\n[4] input "Qty"'
        self.assertEqual(submit.shown_position(page, ["2", "3"]), "3")

    def test_a_step_number_or_an_option_is_no_position(self):
        page = '# Schritt 3 von 8\nPosition 2\n[4] select "Material" options: "M-3"'
        self.assertEqual(submit.shown_position(page, ["2", "3"]), "2")

    def test_a_position_already_entered_is_not_replaced_by_another(self):
        page = '# Angebot - Position 1\n[4] select "Material" options: "M-2"; "M-3"'
        self.assertIsNone(submit.shown_position(page, ["2", "3"], ["1", "2", "3"]))


if __name__ == "__main__":
    unittest.main()

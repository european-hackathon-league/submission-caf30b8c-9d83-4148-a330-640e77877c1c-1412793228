"""The pre-submit check, on invented bids (no scenario values)."""

import unittest
from decimal import Decimal as D

from calculator import Bid, Line
from validate import check


def line(position="1", quantity=10, unit_price="12.34", material="M-1", lead=2):
    return Line(position=position, material_number=material, quantity=quantity,
                unit_price=None if unit_price is None else D(unit_price), lead_time_weeks=lead)


def bid(*lines, total=None, decision="bid", discount="3"):
    total = D(total) if total is not None else sum((D(l.quantity) * l.unit_price for l in lines), D(0))
    return Bid("TEST-0001", decision, D(discount), list(lines), total)


class Repairs(unittest.TestCase):
    def test_a_clean_bid_passes_unchanged(self):
        fixed, issues = check(bid(line("1"), line("2", 4, "100.01")), {"1", "2"})
        self.assertEqual(issues, [])
        self.assertEqual(fixed.total_net, D("523.44"))

    def test_a_duplicate_position_is_dropped(self):
        fixed, issues = check(bid(line("1"), line("1")), {"1"})
        self.assertEqual([l.position for l in fixed.lines], ["1"])
        self.assertEqual(fixed.total_net, D("123.40"))
        self.assertTrue(any("twice" in i for i in issues))

    def test_a_position_the_tender_does_not_have_is_dropped(self):
        fixed, issues = check(bid(line("1"), line("9")), {"1", "2"})
        self.assertEqual([l.position for l in fixed.lines], ["1"])
        self.assertTrue(any("not in the tender" in i for i in issues))

    def test_a_total_that_does_not_add_up_is_replaced_by_the_sum(self):
        fixed, issues = check(bid(line("1"), total="999.99"), {"1"})
        self.assertEqual(fixed.total_net, D("123.40"))
        self.assertTrue(issues)

    def test_a_broken_line_is_omitted_not_entered(self):
        fixed, issues = check(bid(line("1"), line("2", 0)), {"1", "2"})
        self.assertEqual([l.position for l in fixed.lines], ["1"])
        self.assertIn("2", fixed.omitted)

    def test_a_negative_optional_field_is_left_blank(self):
        broken = line("1")
        broken.rebate_total = D("-1")
        fixed, _ = check(bid(broken), {"1"})
        self.assertIsNone(fixed.lines[0].rebate_total)

    def test_a_no_bid_has_no_positions_and_total_zero(self):
        fixed, issues = check(bid(line("1"), decision="no_bid"))
        self.assertEqual((fixed.lines, fixed.total_net), ([], D(0)))
        self.assertTrue(issues)

    def test_without_the_tender_list_only_duplicates_are_dropped(self):
        fixed, _ = check(bid(line("1"), line("7")), None)
        self.assertEqual(len(fixed.lines), 2)


if __name__ == "__main__":
    unittest.main()

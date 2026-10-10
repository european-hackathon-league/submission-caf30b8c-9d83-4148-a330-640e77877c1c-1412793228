"""Tests for the local scorer, on an invented scenario (no real scenario values)."""

import copy
import unittest
from decimal import Decimal

from scorer import score

GOLDEN = {
    "tender_reference": "XX-0000-0001",
    "decision": "bid",
    "currency": "EUR",
    "discount_percent": 3,
    "positions": [
        {"position": "1", "material_number": "M-1", "quantity": 10, "unit_price": 12.34, "lead_time_weeks": 2,
         "base_unit_price": 12.00, "surcharge_per_unit": 1.00, "packaging_per_unit": 0.50, "rebate_total": 0.00},
        {"position": "2", "material_number": "M-2", "quantity": 4, "unit_price": 100.01, "lead_time_weeks": 6,
         "base_unit_price": 99.00, "surcharge_per_unit": 2.50, "packaging_per_unit": 1.25, "rebate_total": 3.10},
    ],
    "total_net": 523.44,  # 10 x 12.34 + 4 x 100.01
    "_checks": {"withdrawn_qa": {"position": "2", "quantity": 4},
                "metal_index": {"position": "1", "field": "surcharge_per_unit"}},
}


def answer_from(golden):
    a = copy.deepcopy(golden)
    a.pop("_checks", None)
    return a


class PerfectAnswer(unittest.TestCase):
    def test_scores_100(self):
        self.assertEqual(score(answer_from(GOLDEN), GOLDEN).quality, Decimal(100))

    def test_zero_width_characters_in_identifiers_still_match(self):
        a = answer_from(GOLDEN)
        a["tender_reference"] = "XX-" + chr(0x200B) + "0000-0001"
        a["positions"][0]["material_number"] = "M" + chr(0x200C) + "-1"
        self.assertEqual(score(a, GOLDEN).quality, Decimal(100))


class PartialCredit(unittest.TestCase):
    def test_blank_optional_field_loses_only_its_weight(self):
        a = answer_from(GOLDEN)
        a["positions"][0].pop("rebate_total")
        share = Decimal(75 - 10) / 2
        self.assertEqual(score(a, GOLDEN).quality, Decimal(100) - share * Decimal("0.10"))

    def test_one_cent_off_unit_price_breaks_unit_price_total_and_arithmetic_only_where_affected(self):
        a = answer_from(GOLDEN)
        a["positions"][0]["unit_price"] = 12.35
        s = score(a, GOLDEN)
        self.assertEqual(s.parts["total"], 5)  # total still matches the golden total
        self.assertEqual(s.parts["arithmetic"], 0)  # but no longer equals the sum of the lines
        self.assertLess(s.parts["position:1"], Decimal(65) / 2)

    def test_omitted_position_gets_nothing_but_others_keep_credit(self):
        a = answer_from(GOLDEN)
        a["positions"] = a["positions"][:1]
        s = score(a, GOLDEN)
        self.assertEqual(s.parts["position:2"], 0)
        self.assertEqual(s.parts["position:1"], Decimal(65) / 2)

    def test_extra_position_costs_one_share(self):
        a = answer_from(GOLDEN)
        a["positions"].append(dict(a["positions"][0], position="9"))
        self.assertEqual(score(a, GOLDEN).quality, Decimal(100) - Decimal(65) / 2 - 5)  # the share, plus arithmetic

    def test_duplicate_position_costs_one_share(self):
        a = answer_from(GOLDEN)
        a["positions"].append(dict(a["positions"][1]))
        self.assertEqual(score(a, GOLDEN).quality, Decimal(100) - Decimal(65) / 2 - 5)  # the share, plus arithmetic

    def test_wrong_reference_is_flagged_not_eligible(self):
        a = answer_from(GOLDEN)
        a["tender_reference"] = "XX-0000-0001-A"
        s = score(a, GOLDEN)
        self.assertEqual(s.parts["reference"], 0)
        self.assertTrue(any("NOT ELIGIBLE" in n for n in s.notes))

    def test_checks_are_scored_separately(self):
        a = answer_from(GOLDEN)
        a["positions"][1]["quantity"] = 5  # used the withdrawn Q&A quantity
        s = score(a, GOLDEN)
        self.assertEqual(s.parts["check:withdrawn_qa"], 0)
        self.assertEqual(s.parts["check:metal_index"], 5)


class NoBid(unittest.TestCase):
    GOLDEN_NO_BID = {"tender_reference": "XX-0000-0002", "decision": "no_bid", "currency": "EUR",
                     "discount_percent": 0, "positions": [], "total_net": 0}

    def test_correct_no_bid_scores_100(self):
        self.assertEqual(score(dict(self.GOLDEN_NO_BID), self.GOLDEN_NO_BID).quality, Decimal(100))

    def test_bidding_when_no_bid_is_right_loses_most(self):
        a = answer_from(GOLDEN)
        a["tender_reference"] = "XX-0000-0002"
        self.assertEqual(score(a, self.GOLDEN_NO_BID).quality, Decimal(5))


if __name__ == "__main__":
    unittest.main()


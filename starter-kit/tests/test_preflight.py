"""Synthetic review-page variations for the last, non-submitting portal check."""
import unittest
from decimal import Decimal

from calculator import Bid, Line
from preflight import check


def bid() -> Bid:
    line = Line("1", "M-1", 40, unit_price=Decimal("12.50"), lead_time_weeks=3)
    return Bid("T-0001", "bid", Decimal("2.5"), [line], Decimal("500.00"))


class ReviewPages(unittest.TestCase):
    def test_renamed_and_reordered_review_fields_still_pass(self):
        page = "Bestellübersicht\nEUR 500,00\nArtikel 1 / M-1\nVorgang T-0001\n[8] button \"Endgültig bestätigen\""
        report = check(page, bid(), "T-0001")
        self.assertTrue(report.ready, report.text())

    def test_visible_validation_error_and_required_input_block_finalisation(self):
        page = ('T-0001\nPosition 1\nTotal 500.00\n'
                '[3] input "VAT ID" value="" (required)\n(error) Please complete highlighted fields')
        report = check(page, bid(), "T-0001")
        self.assertFalse(report.ready)
        self.assertEqual(len(report.blockers), 2)

    def test_incomplete_review_blocks_finalisation_until_summary_is_visible(self):
        report = check('[9] button "Continue"', bid(), "T-0001")
        self.assertFalse(report.ready)
        self.assertEqual(len(report.blockers), 3)
        self.assertIn("tender reference", " ".join(report.blockers))
        self.assertIn("position", " ".join(report.blockers))
        self.assertIn("total", " ".join(report.blockers))

    def test_no_bid_does_not_require_a_line_total(self):
        no_bid = Bid("T-0001", "no_bid", Decimal("0"), [], Decimal("0"))
        report = check("Tender T-0001", no_bid, "T-0001")
        self.assertTrue(report.ready, report.text())


if __name__ == "__main__":
    unittest.main()

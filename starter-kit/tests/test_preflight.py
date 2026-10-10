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

    def test_absent_summary_values_warn_without_guessing_a_failure(self):
        report = check('[9] button "Continue"', bid(), "T-0001")
        self.assertTrue(report.ready)
        self.assertGreaterEqual(len(report.warnings), 3)


if __name__ == "__main__":
    unittest.main()

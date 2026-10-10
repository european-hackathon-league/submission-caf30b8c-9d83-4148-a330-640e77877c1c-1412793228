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

    def test_a_page_that_does_not_show_the_bid_is_not_ready_but_reports_no_error(self):
        report = check('[9] button "Continue"', bid(), "T-0001")
        self.assertFalse(report.ready)
        self.assertEqual(report.blockers, ())  # nothing on the page is wrong: it only proves nothing
        self.assertEqual(len(report.unproven), 3)
        self.assertIn("tender reference", " ".join(report.unproven))
        self.assertIn("position", " ".join(report.unproven))
        self.assertIn("total 500.00", " ".join(report.unproven))
        self.assertIn("NOT SHOWN", report.text())
        self.assertIn("review or summary step", report.text())

    def test_a_no_bid_needs_no_line_total(self):
        no_bid = Bid("T-0001", "no_bid", Decimal("0"), [], Decimal("0"))
        report = check("Tender T-0001", no_bid, "T-0001")
        self.assertTrue(report.ready, report.text())

    def test_a_unit_price_the_review_does_not_list_only_warns(self):
        report = check("T-0001\nPosition 1\nTotal 500,00", bid(), "T-0001")
        self.assertTrue(report.ready, report.text())
        self.assertIn("unit price", " ".join(report.warnings))
        shown = check("T-0001\nPosition 1 | 40 x 12,50\nTotal 500,00", bid(), "T-0001")
        self.assertEqual(shown.warnings, ())

    def test_left_out_positions_are_named_for_the_clerk(self):
        partial = bid()
        partial.omitted = ["2"]
        report = check("T-0001\nPosition 1 | 12.50\nTotal 500.00", partial, "T-0001")
        self.assertTrue(report.ready, report.text())
        self.assertIn("left out position(s): 2", " ".join(report.warnings))


if __name__ == "__main__":
    unittest.main()

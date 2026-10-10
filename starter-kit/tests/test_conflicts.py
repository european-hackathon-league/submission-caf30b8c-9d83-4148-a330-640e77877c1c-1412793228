"""Two filed documents that disagree about the same record are reported, on invented values (no scenario values)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import casefile  # noqa: E402


def case() -> casefile.CaseFile:
    return casefile.CaseFile("brief", {"tender_reference": "TEST-0001", "scenario_date": "2030-01-01"})


class Conflicts(unittest.TestCase):
    def test_a_later_document_that_adds_fields_or_repeats_values_is_no_conflict(self):
        facts = case()
        facts.merge("material", {"materials": [{"material_number": "M-1", "bore_mm": 50, "allocation_mass": "1,25"}]})
        account = facts.merge("material", {"materials": [{"material_number": "M-1", "bore_mm": "50", "stroke_mm": 200,
                                                         "allocation_mass": "1.25", "free_stock": None}]})
        self.assertNotIn("CONFLICT", account)  # the same number in another notation is the same value
        self.assertEqual(facts.conflicts, [])
        self.assertEqual(facts.materials["M-1"]["stroke_mm"], 200)

    def test_a_different_value_for_the_same_record_is_reported_and_kept_on_file(self):
        facts = case()
        facts.merge("material", {"materials": [{"material_number": "M-1", "free_stock": 120, "description": "Cylinder"}]})
        account = facts.merge("material", {"materials": [{"material_number": "M-1", "free_stock": 99,
                                                         "description": "Cylinder, double acting"}]})
        self.assertTrue(account.startswith("CONFLICT WITH AN EARLIER DOCUMENT"), account)
        self.assertIn("material M-1 free_stock: 120 on an earlier document, 99 on this one", account)
        self.assertIn("M-1: free_stock=99", account)  # the ordinary account still follows
        self.assertNotIn("description", " ".join(facts.conflicts))  # wording is not a fact
        self.assertEqual(facts.materials["M-1"]["free_stock"], 99)  # the value filed last is in use, as before
        self.assertEqual(json.loads(facts.dump())["conflicts"], facts.conflicts)

    def test_positions_revisions_and_requirements_are_watched_too(self):
        facts = case()
        facts.merge("positions", {"positions": [{"position": "1", "quantity": 4, "requirement_ref": "REQ-1"}]})
        facts.merge("positions", {"positions": [{"position": "1", "quantity": 40, "requirement_ref": "REQ-1"}]})
        facts.merge("revisions", {"revisions": [{"revision": "B", "status": "current"}]})
        facts.merge("revisions", {"revisions": [{"revision": "B", "status": "superseded"}]})
        facts.merge("requirements", {"revision": "B", "requirements": [{"requirement_ref": "REQ-1", "stroke_mm": 200}]})
        facts.merge("requirements", {"revision": "B", "requirements": [{"requirement_ref": "REQ-1", "stroke_mm": 250}]})
        facts.merge("requirements", {"revision": "C", "requirements": [{"requirement_ref": "REQ-1", "stroke_mm": 300}]})
        self.assertEqual([text.split(":")[0] for text in facts.conflicts],
                         ["position 1 quantity", "revision B status", "requirement REQ-1 in revision B stroke_mm"])


if __name__ == "__main__":
    unittest.main()

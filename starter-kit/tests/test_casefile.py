"""Evidence provenance remains attached to the extracted facts it produced."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import casefile  # noqa: E402
import llm  # noqa: E402


class EvidenceProvenance(unittest.IsolatedAsyncioTestCase):
    async def test_successful_extraction_records_its_source_and_typed_result(self):
        facts = casefile.CaseFile("brief", {"tender_reference": "TEST-0001", "scenario_date": "2030-01-01"})

        async def extracted(*args, **kwargs):
            return {"positions": [{"position": "1", "quantity": 4, "requirement_ref": "REQ-1"}]}

        with patch.object(llm, "chat_json", extracted):
            await facts._extract("positions", "Position 1: four items", "https://portal.example/rfq", "tender", "abc123")
        [evidence] = facts.evidence
        self.assertEqual((evidence["id"], evidence["kind"], evidence["source"], evidence["agent"]),
                         ("abc123", "positions", "https://portal.example/rfq", "tender"))
        self.assertEqual(evidence["extracted"]["positions"][0]["position"], "1")
        self.assertEqual(json.loads(facts.dump())["evidence"][0]["source"], "https://portal.example/rfq")


if __name__ == "__main__":
    unittest.main()

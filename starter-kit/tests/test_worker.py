"""The generic action verifier must expose silent portal failures to the model."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import llm  # noqa: E402
from worker import Agent, state_fingerprint  # noqa: E402


class FakeTab:
    def __init__(self, change_on_fill: bool):
        self.base_url = "http://portal.test"
        self.page = SimpleNamespace(url=self.base_url, main_frame=SimpleNamespace(evaluate=self._alive))
        self.document, self.document_source = "", ""
        self.change_on_fill = change_on_fill
        self.view = 'url: http://portal.test\ntitle: Form\n[1] input "Name" value=""'

    async def _alive(self, script):
        return True

    async def observe(self):
        return self.view

    def take_events(self):
        return []

    async def fill(self, aid, text, enter=False):
        if self.change_on_fill:
            self.view = f'url: http://portal.test\ntitle: Form\n[1] input "Name" value="{text}"'
        return f"filled [{aid}]"


class ActionVerification(unittest.IsolatedAsyncioTestCase):
    async def run_agent(self, change_on_fill: bool):
        replies = [
            {"thought": "", "actions": [{"do": "fill", "id": 1, "text": "Ada"}]},
            {"thought": "", "actions": [{"do": "done", "summary": "checked"}]},
        ]
        asked = []

        async def model(messages, **kwargs):
            asked.append(messages[-1]["content"])
            return replies.pop(0)

        with patch.object(llm, "chat_json", model):
            outcome = await Agent("test", FakeTab(change_on_fill), "system", lambda: "job", max_steps=4).run()
        return outcome, asked

    async def test_changed_form_state_is_reported(self):
        outcome, asked = await self.run_agent(True)
        self.assertTrue(outcome["done"])
        self.assertIn("verification: fill visibly changed the page state", asked[1])

    async def test_silent_noop_is_reported_with_a_recovery_hint(self):
        outcome, asked = await self.run_agent(False)
        self.assertTrue(outcome["done"])
        self.assertIn("verification: fill caused no visible page change", asked[1])
        self.assertIn("instead of repeating it blindly", asked[1])

    def test_generated_action_ids_do_not_count_as_a_state_change(self):
        first = 'url: http://portal.test\n[1] button "Continue"'
        reread = 'url: http://portal.test\n[48] button "Continue"'
        self.assertEqual(state_fingerprint(first), state_fingerprint(reread))


if __name__ == "__main__":
    unittest.main()

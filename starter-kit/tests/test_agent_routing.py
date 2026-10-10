"""Specialized investigators wake only for questions their portal can answer."""
import asyncio
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent  # noqa: E402
from agent import Team, questions_for_site  # noqa: E402


class FakeCase:
    def __init__(self):
        self.version = 0
        self.pending = 0
        self.news = {}
        self.open_questions = [("mailbox", "Find the sales mailbox.")]
        self.changed = asyncio.Event()

    def questions(self):
        return list(self.open_questions)

    async def wait_change(self, seen, timeout):
        if self.version == seen:
            try:
                await asyncio.wait_for(self.changed.wait(), timeout)
            except asyncio.TimeoutError:
                return False
            self.changed.clear()
        return self.version != seen

    def update(self, question):
        self.open_questions.append(question)
        self.version += 1
        self.changed.set()


class QuestionRouting(unittest.IsolatedAsyncioTestCase):
    def test_erp_and_mail_receive_only_resolvable_questions(self):
        questions = [
            ("positions", "Find tender positions."),
            ("material:REQ-1", "Find a matching ERP material."),
            ("data:MAT-1", "Find missing ERP data."),
            ("discount", "Find discount approval."),
            ("reserve:REQ-2", "Find technical release."),
        ]

        self.assertEqual([qid for qid, _ in questions_for_site("erp", questions)],
                         ["material:REQ-1", "data:MAT-1"])
        self.assertEqual([qid for qid, _ in questions_for_site("mail", questions)],
                         ["discount", "reserve:REQ-2"])
        self.assertEqual(questions_for_site("new-portal", questions), questions)

    def test_routing_follows_the_roles_read_from_the_brief_not_the_site_names(self):
        """The private dataset uses other site names (brief: other software, layout and site names)."""
        questions = [("positions", "p"), ("material:REQ-1", "m"), ("discount", "d"), ("reserve:REQ-2", "r")]
        try:
            agent.SITE_ROLES.update({"erp": "warenwirtschaft", "mail": "postfach"})
            self.assertEqual([q for q, _ in questions_for_site("warenwirtschaft", questions)], ["material:REQ-1"])
            self.assertEqual([q for q, _ in questions_for_site("postfach", questions)], ["discount", "reserve:REQ-2"])
            # a site that merely contains "mail" in its name but is not the mailbox gets everything
            self.assertEqual(questions_for_site("mailing-list-portal", questions), questions)
        finally:
            agent.SITE_ROLES.clear()


    async def test_erp_idle_hook_ignores_new_mail_questions(self):
        case = FakeCase()
        team = Team(case, ["erp"], time.time() + 5)
        hook = team.hook("erp")
        waiting = asyncio.create_task(hook("done"))
        await asyncio.sleep(0)

        case.update(("discount", "Find discount approval."))
        await asyncio.sleep(0.02)
        self.assertFalse(waiting.done())

        case.update(("material:REQ-1", "Find a matching ERP material."))
        self.assertIn("material:REQ-1", await waiting)


if __name__ == "__main__":
    unittest.main()

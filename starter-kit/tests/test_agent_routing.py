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
        """As CaseFile.wait_change: clear first, then wait, so an old signal does not count as a new change."""
        if self.version == seen:
            self.changed.clear()
            try:
                await asyncio.wait_for(self.changed.wait(), timeout)
            except asyncio.TimeoutError:
                return False
        return self.version != seen

    def update(self, question):
        self.open_questions.append(question)
        self.version += 1
        self.changed.set()


class QuestionRouting(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        agent.SITE_ROLES.clear()
        agent.RELEASED.clear()
        agent.TOPIC_SITES.clear()

    tearDown = setUp

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
            # a site that merely contains "mail" in its name but is not the mailbox gets everything but the mail
            # records: those belong to the mailbox the brief names (run 72e78b8e)
            self.assertEqual([q for q, _ in questions_for_site("mailing-list-portal", questions)],
                             ["positions", "material:REQ-1"])
        finally:
            agent.SITE_ROLES.clear()


    async def test_a_routed_question_left_open_is_offered_to_every_agent(self):
        """A non-mail question its routed agent left open reaches every agent; a mail record whose website the brief
        names stays with that website (run 72e78b8e: released reserve questions were bounced by the ERP agent)."""
        case = FakeCase()
        case.open_questions = [("packaging_tariff:PKG-9", "the tariff"), ("material:REQ-1", "the material")]
        case._bump = lambda: (setattr(case, "version", case.version + 1), case.changed.set())
        team = Team(case, ["erp", "mail"], time.time() + 5)
        try:
            agent.SITE_ROLES.update({"erp": "erp", "mail": "mail"})
            erp_waiting = asyncio.create_task(team.hook("erp")("done"))  # ERP finished its own question set
            await asyncio.sleep(0.02)
            self.assertIn("material:REQ-1", agent.RELEASED)  # ERP went idle with it open and nothing being read
            self.assertIn("material:REQ-1", [q for q, _ in questions_for_site("mail", case.questions())])
            mail_waiting = asyncio.create_task(team.hook("mail")("done"))  # mail finished without the tariff
            await asyncio.sleep(0.05)
            self.assertNotIn("packaging_tariff:PKG-9", agent.RELEASED)
            self.assertNotIn("packaging_tariff:PKG-9", [q for q, _ in questions_for_site("erp", case.questions())])
            self.assertIn("packaging_tariff:PKG-9", [q for q, _ in questions_for_site("mail", case.questions())])
            erp_waiting.cancel()
            mail_waiting.cancel()
        finally:
            agent.SITE_ROLES.clear()
            agent.RELEASED.clear()

    def test_a_topic_the_brief_keeps_on_another_website_goes_there(self):
        """The private dataset may split facts differently (eval variant B: an approval register in the ERP): the
        brief's record_sites send that topic's questions to that website's agent alone."""
        questions = [("packaging_tariff:PKG-9", "t"), ("discount", "d"), ("material:REQ-1", "m")]
        try:
            agent.SITE_ROLES.update({"erp": "erp", "mail": "mail"})
            agent.TOPIC_SITES.update({"packaging_tariffs": "erp"})
            self.assertEqual([q for q, _ in questions_for_site("erp", questions)],
                             ["packaging_tariff:PKG-9", "material:REQ-1"])
            self.assertEqual([q for q, _ in questions_for_site("mail", questions)], ["discount"])
            self.assertEqual([q for q, _ in questions_for_site("portal", questions)], ["material:REQ-1"])
        finally:
            agent.SITE_ROLES.clear()
            agent.TOPIC_SITES.clear()

    def test_nothing_is_released_while_documents_are_still_being_read(self):
        case = FakeCase()
        case.open_questions = [("packaging_tariff:PKG-9", "the tariff")]
        case.pending = 1
        Team(case, ["mail"], time.time() + 5).release("mail", {"packaging_tariff:PKG-9"})
        self.assertEqual(agent.RELEASED, set())

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

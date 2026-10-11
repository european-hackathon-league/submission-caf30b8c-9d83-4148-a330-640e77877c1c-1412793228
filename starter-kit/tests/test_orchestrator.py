"""The coordinator model (orchestrator.py) hands out work at events: an idle agent gets a task and is woken, a question
nobody works on is assigned, and the investigation does not end while the coordinator says work is left (bounded).
With ORCHESTRATOR=0 nothing changes. Scripted model, invented sites and values."""
import asyncio
import os
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent  # noqa: E402
import llm  # noqa: E402
import orchestrator  # noqa: E402
from agent import Team, investigator, questions_for_site  # noqa: E402
from casefile import CaseFile  # noqa: E402
from test_paged_keep import Viewer  # noqa: E402


class FakeCase:
    def __init__(self, questions=()):
        self.version = 0
        self.pending = 0
        self.news = {}
        self.answers = {}
        self.evidence = []
        self.brief = "Bid for tender T-1."
        self.open_questions = list(questions)
        self.facts = "nothing on file"
        self.changed = asyncio.Event()

    def questions(self):
        return list(self.open_questions)

    def status(self, sections=None):
        return f"Tender T-1. {self.facts}"

    async def wait_change(self, seen, timeout):
        if self.version == seen:
            self.changed.clear()
            try:
                await asyncio.wait_for(self.changed.wait(), timeout)
            except asyncio.TimeoutError:
                return False
        return self.version != seen

    def _bump(self):
        self.version += 1
        self.changed.set()


class Coordinator:
    """Stands in for the coordinator's model: the next scripted reply per call, and the prompts it was shown."""

    def __init__(self, *replies, repeat=None):
        self.replies, self.repeat, self.prompts = list(replies), repeat, []

    async def __call__(self, messages, *, think=True, max_tokens=6000, label=""):
        assert label == "orchestrator"
        self.prompts.append(messages[-1]["content"])
        if self.replies:
            return self.replies.pop(0)
        return dict(self.repeat) if self.repeat else {}


def team_with(case, names, chat, roles=None, seconds=300):
    team = Team(case, names, time.time() + seconds)
    sites = {name: {"url": f"http://{name}.test", "role": (roles or {}).get(name, "general")} for name in names}
    team.orch = orchestrator.Orchestrator(case, sites, case.brief, questions_for_site, team.deadline, chat=chat)
    return team


async def until(condition, seconds=5.0):
    end = time.time() + seconds
    while not condition() and time.time() < end:
        await asyncio.sleep(0.02)
    return condition()


class Events(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        agent.SITE_ROLES.clear()
        agent.RELEASED.clear()
        agent.TOPIC_SITES.clear()
        self.debounce = patch.object(orchestrator, "DEBOUNCE", 0.0)
        self.debounce.start()

    def tearDown(self):
        self.debounce.stop()
        agent.SITE_ROLES.clear()
        agent.RELEASED.clear()
        agent.TOPIC_SITES.clear()

    async def test_an_idle_erp_gets_a_task_when_requirements_without_a_group_arrive_and_is_woken(self):
        """Eval run_59d51b28: the requirements came without a catalogue group, so no material question opened and
        the idle ERP agent was never woken. The coordinator sees the values on file and hands it the search."""
        agent.SITE_ROLES.update({"erp": "erp", "mail": "mail"})
        case = FakeCase([("requirements", "the requirements R-1 in full: catalogue group")])
        task = "search the material master by bore 40, stroke 200; file each candidate's status, stock and prices"
        chat = Coordinator({"tasks": [], "investigation_complete": False, "reason": "waiting for requirements"},
                           {"tasks": [{"agent": "ERP", "task": task}], "investigation_complete": False,
                            "reason": "requirement values are on file"})
        team = team_with(case, ["erp", "portal", "mail"], chat, {"erp": "erp", "mail": "mail"})
        erp = asyncio.create_task(team.hook("erp")("done"))
        await until(lambda: len(chat.prompts) == 1)
        self.assertIn("erp went idle", chat.prompts[0])
        self.assertIn("-> portal", chat.prompts[0])  # the requirements question is routed to the portal, not the ERP
        self.assertFalse(erp.done())
        case.facts = "Requirement R-1: bore 40 mm, stroke 200 mm, catalogue group unknown"
        case._bump()  # the portal filed the requirements
        news = await asyncio.wait_for(erp, 5)
        self.assertEqual(news, f"TASK FROM THE COORDINATOR: {task}")
        self.assertIn("new facts on file while erp idle", chat.prompts[1])
        self.assertIn("catalogue group unknown", chat.prompts[1])
        self.assertIn(task, team.orch.briefing_line("erp"))
        team.finished.set()

    async def test_a_bounced_question_is_assigned_to_the_mail_agent_before_the_end(self):
        """Run 72e78b8e: the reserve question bounced between the ERP and the mail agent. Every agent went idle;
        the coordinator reads why and gives the search to the mail agent instead of ending."""
        agent.SITE_ROLES.update({"erp": "erp", "mail": "mail"})
        case = FakeCase([("reserve:R-2", "the technical release for R-2")])
        task = "search inbox and archive for 'T-1 release' and file every hit"
        chat = Coordinator({"tasks": [], "investigation_complete": False, "reason": "the ERP is still working"},
                           {"tasks": [{"agent": "mail", "task": task}], "investigation_complete": False,
                            "reason": "nobody searched the release"})
        team = team_with(case, ["erp", "mail"], chat, {"erp": "erp", "mail": "mail"})
        team.orch.agents["erp"] = SimpleNamespace(turns=[], finish_summary="the release records belong to the mail site")
        mail = asyncio.create_task(team.hook("mail")("done"))
        await until(lambda: len(chat.prompts) == 1)
        erp = asyncio.create_task(team.hook("erp")("done"))  # the last one to go idle: the end check asks
        news = await asyncio.wait_for(mail, 8)
        self.assertEqual(news, f"TASK FROM THE COORDINATOR: {task}")
        self.assertIn("every agent is idle", chat.prompts[1])
        self.assertIn("belong to the mail site", chat.prompts[1])
        self.assertFalse(team.finished.is_set())
        self.assertEqual(team.orch.extensions, 1)
        team.finished.set()
        await asyncio.wait_for(erp, 3)

    async def test_the_investigation_does_not_end_while_incomplete_but_only_twice(self):
        case = FakeCase([("discount", "the discount approval")])
        chat = Coordinator(repeat={"tasks": [{"agent": "portal", "task": "file the amendment notices"}],
                                   "investigation_complete": False, "reason": "amendments missing"})
        team = team_with(case, ["portal"], chat)
        for round_ in (1, 2):
            news = await asyncio.wait_for(team.hook("portal")("done"), 8)
            self.assertIn("file the amendment notices", news)
            self.assertFalse(team.finished.is_set())
            self.assertEqual(team.orch.extensions, round_)
            team.orch.briefing_line("portal")
        self.assertIsNone(await asyncio.wait_for(team.hook("portal")("done"), 8))  # third time: it ends
        self.assertTrue(team.finished.is_set())
        self.assertEqual(len(chat.prompts), 2)  # no call once the extensions are used up
        self.assertIn("file the amendment notices -> finished", chat.prompts[1])

    async def test_a_complete_investigation_ends_after_one_call(self):
        case = FakeCase()
        chat = Coordinator({"tasks": [], "investigation_complete": True, "reason": "all facts on file"})
        team = team_with(case, ["portal", "erp"], chat)
        first = asyncio.create_task(team.hook("portal")("done"))
        await until(lambda: len(chat.prompts) == 1)
        second = asyncio.create_task(team.hook("erp")("done"))
        self.assertIsNone(await asyncio.wait_for(second, 8))
        self.assertIsNone(await asyncio.wait_for(first, 3))
        self.assertTrue(team.finished.is_set())
        self.assertEqual(len(chat.prompts), 2)  # portal idle, then the end check

    async def test_calls_are_bounded_and_unchanged_situations_are_not_asked_again(self):
        case = FakeCase()
        chat = Coordinator(repeat={"tasks": []})
        orch = orchestrator.Orchestrator(case, {"portal": {"url": "u", "role": "general"}}, "", questions_for_site,
                                         time.time() + 300, chat=chat)
        self.assertEqual(await orch.consult("a"), {})
        self.assertIsNone(await orch.consult("b"))  # nothing changed since the last call
        for _ in range(40):
            case._bump()
            await orch.consult("facts")
        self.assertEqual(orch.calls, orchestrator.MAX_CALLS - orchestrator.END_RESERVE)
        self.assertEqual(await orch.consult("end", final=True), {})  # the end checks keep their reserve
        self.assertEqual(orch.calls, orchestrator.MAX_CALLS - orchestrator.END_RESERVE + 1)

    def test_tasks_for_unknown_agents_or_without_text_are_dropped(self):
        orch = orchestrator.Orchestrator(FakeCase(), {"erp": {}, "mail": {}}, "", questions_for_site, time.time() + 300)
        given = orch.apply({"tasks": [{"agent": "Mail", "task": "  search  it "}, {"agent": "nowhere", "task": "x"},
                                      {"agent": "erp", "task": ""}, "junk"]})
        self.assertEqual(given, {"mail": "search it"})
        self.assertEqual(orch.apply("not json"), {})


class Switch(unittest.IsolatedAsyncioTestCase):
    def test_the_switch(self):
        for value, on in (("0", False), ("off", False), ("1", True), ("", orchestrator.DEFAULT_ON)):
            with patch.dict(os.environ, {"ORCHESTRATOR": value}):
                self.assertEqual(orchestrator.enabled(), on)

    async def test_without_a_coordinator_the_team_ends_as_before(self):
        case = FakeCase([("discount", "d")])
        team = Team(case, ["portal"], time.time() + 5)
        self.assertIsNone(team.orch)
        with patch.object(llm, "chat_json", side_effect=AssertionError("no model call")):
            self.assertIsNone(await asyncio.wait_for(team.hook("portal")("done"), 3))
        self.assertTrue(team.finished.is_set())

    async def test_the_task_heads_the_briefing_above_the_open_questions(self):
        case = CaseFile("Bid for tender T-1.", {"tender_reference": "T-1", "scenario_date": "2030-01-15"})
        case.questions = lambda: [("revision", "the revision history")]
        orch = orchestrator.Orchestrator(case, {"portal": {}}, "", questions_for_site, time.time() + 300)
        orch.apply({"tasks": [{"agent": "portal", "task": "open the amendment notices and file them"}]})
        asked = []

        async def model(messages, **kwargs):
            asked.append(messages[-1]["content"])
            return {"thought": "t", "actions": [{"do": "done", "summary": "filed the notices"}]}

        async def idle(why):
            return None

        team = SimpleNamespace(hook=lambda name: idle, orch=orch)
        with patch.object(llm, "chat_json", model), patch.dict(os.environ, {"AGENT_MAX_STEPS": "3"}):
            outcome = await investigator(case, team, Viewer(), time.time() + 600).run()
        self.assertTrue(outcome["done"])
        text = asked[0]
        self.assertIn("TASK FROM THE COORDINATOR", text)
        self.assertLess(text.index("open the amendment notices"), text.index("OPEN QUESTIONS"))
        self.assertEqual(orch.agents["portal"].finish_summary, "filed the notices")

    async def test_without_a_coordinator_the_briefing_has_no_task(self):
        case = CaseFile("Bid for tender T-1.", {"tender_reference": "T-1", "scenario_date": "2030-01-15"})
        case.questions = lambda: []
        asked = []

        async def model(messages, **kwargs):
            asked.append(messages[-1]["content"])
            return {"thought": "t", "actions": [{"do": "done", "summary": "nothing to do"}]}

        async def idle(why):
            return None

        with patch.object(llm, "chat_json", model), patch.dict(os.environ, {"AGENT_MAX_STEPS": "3"}):
            await investigator(case, SimpleNamespace(hook=lambda name: idle), Viewer(), time.time() + 600).run()
        self.assertNotIn("COORDINATOR", asked[0])


if __name__ == "__main__":
    unittest.main()

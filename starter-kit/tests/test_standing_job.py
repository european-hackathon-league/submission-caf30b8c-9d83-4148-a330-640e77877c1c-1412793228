"""The lean investigator prompt keeps each agent's standing job, and question generation covers a world without
catalogue groups. Eval variant B: the requirements name no catalogue group and no pressure, so no material question
arose; the ERP agent finished at turn 2 with nothing filed and was never woken, and the customer-portal agent hunted
for fields the specification does not have. Variant A: the mail agent finished without the buyer's quantity change.
Public run 0cd32dc4: the token budget stopped every investigator with questions open.

All references, sites and values here are invented."""
import asyncio
import os
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent  # noqa: E402
import llm  # noqa: E402
from agent import Team  # noqa: E402
from casefile import CaseFile, brief_site_lines  # noqa: E402

BRIEF = """# Quote the gadgets

Prepare one bid for tender ZT-31 of the town of Elsewhere. The scenario date is 2031-05-02T08:00:00Z.

## Where things are

The bill of quantities sits on `bids-hub`. Articles, stock and prices are kept in `wawi`, which also holds the
register of discount releases. The buyer's change requests arrive in `inbox-x`.

## Rules

1. Quantity: the latest change applies.
2. Material: an active article whose attributes equal the requirement.
"""

CONTEXT = {"tender_reference": "ZT-31", "scenario_date": "2031-05-02T08:00:00Z", "company_name": "Gadget Co",
           "mail_site": "inbox-x", "erp_site": "wawi", "authorized_senders": {"discount_approval": "chief"}}


def world_without_groups(with_requirements: bool = True) -> CaseFile:
    case = CaseFile(BRIEF, CONTEXT)
    case.merge("positions", {"positions": [{"position": "10", "quantity": 7, "unit": "pcs", "requirement_ref": "Q-1"}]})
    case.merge("revisions", {"revisions": [{"revision": "C", "status": "current", "date": "2031-01-01"}]})
    if with_requirements:
        case.merge("requirements", {"revision": "C", "requirements": [
            {"requirement_ref": "Q-1", "bore_mm": 32, "stroke_mm": 80, "mounting": "clevis"}]})
    return case


def make(site: str, case: CaseFile, env: dict | None = None):
    agent.SITE_ROLES.clear()
    agent.SITE_ROLES.update({"erp": "wawi", "mail": "inbox-x"})
    tab = SimpleNamespace(site_id=site, base_url=f"https://{site}.test", page=SimpleNamespace(url=""))
    with patch.dict(os.environ, env or {}):
        return agent.investigator(case, SimpleNamespace(hook=lambda name: None), tab, time.time() + 600)


class WorldWithoutCatalogueGroups(unittest.TestCase):
    def test_a_material_question_arises_from_bore_stroke_and_mounting(self):
        questions = dict(world_without_groups().questions())
        self.assertIn("material:Q-1", questions)
        self.assertIn("names no catalogue group", questions["material:Q-1"])
        self.assertNotIn("None", questions["material:Q-1"])

    def test_the_requirements_question_closes_without_pressure_or_group(self):
        self.assertNotIn("requirements", dict(world_without_groups().questions()))
        without = dict(world_without_groups(with_requirements=False).questions())
        self.assertIn("requirements", without)

    def test_absent_is_judged_on_candidates_of_the_same_bore(self):
        case = world_without_groups()
        case.merge("material", {"materials": [{"material_number": "AR-5", "is_active": True, "bore_mm": 32,
                                               "stroke_mm": 90, "pressure_bar": 10, "mounting": "clevis"}]})
        result = case.answer("material:Q-1", "absent", "none fits", agent="wawi")
        self.assertNotIn("catalogue group is on file", result)
        self.assertIn("closed as absent", result)


class StandingJob(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        agent.SITE_ROLES.clear()

    async def test_the_erp_agent_knows_its_standing_job_and_may_not_finish_with_nothing_filed(self):
        case = world_without_groups(with_requirements=False)
        case.questions = lambda: []  # nothing routed to it yet
        erp = make("wawi", case)
        self.assertIn("ERP or inventory system", erp.system)
        self.assertIn("approvals, releases or registers", erp.system)
        self.assertIn("register of discount releases", erp.system)  # the brief's own sentence on its website
        first = await erp.before_done({"do": "done"})
        self.assertIn("nothing from this website is in the case file yet", first)
        self.assertEqual(erp.gates.gate, 1)  # more context instead of finishing
        second = await erp.before_done({"do": "done"})
        self.assertTrue(second.startswith("not finished"))
        self.assertIsNone(await erp.before_done({"do": "done"}))  # bounded

    async def test_the_mail_agent_is_reminded_of_the_buyers_changes_once(self):
        case = world_without_groups()
        case.questions = lambda: []
        mail = make("inbox-x", case)
        self.assertIn("changes the tender", mail.system)
        self.assertIn("change requests arrive", mail.system)
        refusal = await mail.before_done({"do": "done"})
        self.assertIn("message from the buyer that changes the tender", refusal)

    async def test_gates_off_keep_the_old_done_behaviour(self):
        case = world_without_groups()
        case.questions = lambda: []
        erp = make("wawi", case, {"CONTEXT_GATES": "0"})
        self.assertIsNone(await erp.before_done({"do": "done"}))

    def test_the_site_sentence_is_cut_by_the_site_id(self):
        self.assertIn("register of discount releases", brief_site_lines(BRIEF, "wawi"))
        self.assertEqual(brief_site_lines(BRIEF, "nowhere"), "")
        self.assertEqual(brief_site_lines(BRIEF, "wawi", skip=brief_site_lines(BRIEF, "wawi")), "")


class Waking(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        agent.SITE_ROLES.clear()

    async def idle_then(self, case, site, change):
        agent.SITE_ROLES.clear()
        agent.SITE_ROLES.update({"erp": "wawi", "mail": "inbox-x"})
        team = Team(case, [site, "other"], time.time() + 30)
        hold = asyncio.create_task(team.hook(site)("done"))
        await asyncio.sleep(0.05)
        change()
        return await asyncio.wait_for(hold, 5)

    async def test_an_idle_erp_agent_is_woken_when_requirements_are_filed(self):
        case = world_without_groups(with_requirements=False)
        news = await self.idle_then(case, "wawi", lambda: case.merge("requirements", {"revision": "C", "requirements": [
            {"requirement_ref": "Q-1", "bore_mm": 32, "stroke_mm": 80, "mounting": "clevis"}]}))
        self.assertIsNotNone(news)
        self.assertIn("material:Q-1", news)  # the new question routed to it, named

    async def test_a_new_record_wakes_the_mailbox_agent_without_a_question(self):
        case = world_without_groups()
        case.questions = lambda: []
        news = await self.idle_then(case, "inbox-x", lambda: case.merge("positions", {"positions": [
            {"position": "20", "quantity": 3, "unit": "pcs", "requirement_ref": "Q-1"}]}))
        self.assertIn("standing job", news)


class SoftBudget(unittest.TestCase):
    def setUp(self):
        self.saved = llm.STATS["prompt_tokens"]

    def tearDown(self):
        llm.STATS["prompt_tokens"] = self.saved
        agent.SITE_ROLES.clear()

    def test_the_budget_is_off_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TOKEN_BUDGET", None)
            self.assertEqual(agent.token_budget(), 0)

    def test_never_stop_while_it_owns_an_open_question(self):
        case = world_without_groups()
        erp = make("wawi", case)
        llm.STATS["prompt_tokens"] = 5000
        with patch.dict(os.environ, {"TOKEN_BUDGET": "1000"}):
            self.assertIn("material:Q-1", dict(case.questions()))
            self.assertIsNone(erp.stop_when())
            case.questions = lambda: []
            self.assertEqual(erp.stop_when(), "token budget used up")
            self.assertIn("no browsing beyond your open questions", erp.briefing())


if __name__ == "__main__":
    unittest.main()

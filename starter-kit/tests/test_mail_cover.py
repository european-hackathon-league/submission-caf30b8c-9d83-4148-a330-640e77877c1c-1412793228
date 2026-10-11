"""Every mail topic the brief prescribes is searched once, early; mail records stay with the mailbox agent; FX is asked
for every candidate material. Runs 72e78b8ee563dad4 and 65a5d83baf69cf63: two prescribed topics were never searched,
the reserve questions bounced between the mail and ERP agents, the FX question came too late.

All references, subject words, senders, sites, keys and values here are invented."""
import os
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent  # noqa: E402
import casefile  # noqa: E402
import llm  # noqa: E402
from agent import DONE_REFUSALS, Team, investigator, questions_for_site  # noqa: E402

CONTEXT = {
    "tender_reference": "QK-5150",
    "scenario_date": "2032-06-01T08:00:00Z",
    "mail_site": "postbox",
    "authorized_senders": {"discount_approval": "boss", "tech_release": "workshop", "fx_fixing": "treasury",
                           "packaging_tariffs": "yard", "condition_rules": None, "price_indices": None,
                           "delivery_release": None, "setup_pools": None, "project_bonus": None},
    "authorized_subjects": {"tech_release": "Werkfreigabe", "fx_fixing": "Kursnotiz", "packaging_tariffs": "Kistenpreise",
                            "setup_pools": "Rüstkasse"},
}


def search_ids(case) -> list[str]:
    return [qid for qid, _ in case.questions() if qid.startswith("search:")]


class PrescribedTopics(unittest.TestCase):
    def test_every_named_topic_is_asked_once_before_any_key_is_known(self):
        case = casefile.CaseFile("brief", CONTEXT)
        self.assertEqual(case.prescribed_topics(),
                         ["discount_approval", "tech_release", "packaging_tariffs", "fx_fixing", "setup_pools"])
        # the discount has its own question, which already carries its search words
        self.assertEqual(search_ids(case), ["search:tech_release", "search:packaging_tariffs", "search:fx_fixing",
                                            "search:setup_pools"])
        text = dict(case.questions())["search:fx_fixing"]
        self.assertIn("Search words: QK-5150 Kursnotiz; authorized sender: treasury@", text)
        self.assertIn("the sales mailbox (inbox and archive)", text)

    def test_a_search_naming_the_subject_word_ticks_the_topic_off(self):
        case = casefile.CaseFile("brief", CONTEXT)
        case.note_search("QK-5150 werkfreigabe")  # case does not matter
        case.note_search("QK-5150 Kistenpreis")  # a cut-off form counts
        case.note_search("Ruestkasse")  # umlaut written out
        self.assertEqual(search_ids(case), ["search:fx_fixing"])
        case.note_search("QK-5150 Kurs")  # too short a stem to name the word
        self.assertEqual(search_ids(case), ["search:fx_fixing"])
        case.note_search("Kursnotiz")
        self.assertEqual(search_ids(case), [])

    def test_a_filed_message_or_an_answer_ticks_the_topic_off(self):
        case = casefile.CaseFile("brief", CONTEXT)
        case.merge("mail", {"messages": [{"sender": "workshop@maker.test", "timestamp": "2032-05-01T08:00:00Z",
                                          "subject": "Werkfreigabe QK-9999", "tender_reference": "QK-9999",
                                          "topic": "tech_release"}]})  # another reference: the search found it all the same
        case.answers["search:setup_pools"] = ("absent", "nothing in inbox or archive")
        self.assertEqual(search_ids(case), ["search:packaging_tariffs", "search:fx_fixing"])

    def test_a_topic_with_its_own_question_open_is_not_asked_twice(self):
        case = casefile.CaseFile("brief", CONTEXT)
        case.merge("positions", {"positions": [{"position": "1", "quantity": 4, "unit": "pcs", "requirement_ref": "RQ-7"}]})
        case.merge("clarifications", {"answers": [{"number": "1", "timestamp": "2032-05-01T08:00:00Z",
                                                   "assignments": [{"position": "1", "packaging_tariff": "KP-3"}]}]})
        ids = [qid for qid, _ in case.questions()]
        self.assertIn("packaging_tariff:KP-3", ids)
        self.assertNotIn("search:packaging_tariffs", ids)

    def test_no_topic_named_means_no_search_question(self):
        case = casefile.CaseFile("brief", {"tender_reference": "QK-5150", "scenario_date": "2032-06-01"})
        self.assertEqual(search_ids(case), [])

    def test_the_checklist_marks_topics_not_searched_yet(self):
        case = casefile.CaseFile("brief", CONTEXT)
        case.note_search("QK-5150 Werkfreigabe")
        checklist = case.mail_checklist(case.questions())
        line = next(line for line in checklist.splitlines() if line.startswith("- fx fixing"))
        self.assertTrue(line.endswith("(NOT SEARCHED YET)"))
        self.assertFalse(any(line.startswith("- tech release") for line in checklist.splitlines()))

    def test_a_topic_kept_on_another_website_says_so(self):
        case = casefile.CaseFile("brief", dict(CONTEXT, record_sites={"discount_approval": "ledger", "fx_fixing": 7}))
        self.assertEqual(case.record_sites, {"discount_approval": "ledger"})
        self.assertIn("Where: the website ledger", dict(case.questions())["discount"])
        self.assertNotIn("inbox and the archive", dict(case.questions())["discount"])


class FxForEveryCandidate(unittest.TestCase):
    def test_fx_is_asked_for_a_candidate_that_is_not_selected(self):
        case = casefile.CaseFile("brief", CONTEXT)
        case.merge("material", {"materials": [{"material_number": "M-81", "catalogue_group": "G-2", "is_active": True,
                                               "bore_mm": 30, "stroke_mm": 90}]})
        case.merge("price_conditions", {"material_number": "M-81", "conditions": [
            {"valid_from": "2032-01-01", "valid_to": "2032-12-31", "currency": "SEK", "fx_key": "KN-4",
             "price_unit_pieces": 1, "scales": [{"min_quantity": "1", "price": "12,50"}]},
            {"valid_from": "2031-01-01", "valid_to": "2031-12-31", "currency": "NOK", "fx_key": "KN-1",
             "price_unit_pieces": 1, "scales": [{"min_quantity": "1", "price": "11,00"}]}]})
        questions = dict(case.questions())
        self.assertIn("fx:KN-4", questions)  # no position, no requirement, nothing selected yet
        self.assertNotIn("fx:KN-1", questions)  # not valid on the scenario date
        self.assertIn("SEK, material M-81", questions["fx:KN-4"])
        self.assertIn("the sales mailbox (inbox and archive)", questions["fx:KN-4"])
        case.merge("mail", {"messages": [{"sender": "treasury@maker.test", "timestamp": "2032-05-20T08:00:00Z",
                                          "subject": "Kursnotiz", "tender_reference": "QK-5150", "topic": "fx_fixing",
                                          "fx_fixing": [{"key": "KN-4", "currency": "SEK", "eur_per_unit": "0,09"}]}]})
        self.assertNotIn("fx:KN-4", dict(case.questions()))

    def test_one_fx_key_on_two_materials_is_one_question(self):
        case = casefile.CaseFile("brief", CONTEXT)
        for number in ("M-1", "M-2"):
            case.merge("price_conditions", {"material_number": number, "conditions": [
                {"valid_from": "2032-01-01", "valid_to": "2032-12-31", "currency": "SEK", "fx_key": "KN-4",
                 "price_unit_pieces": 1, "scales": [{"min_quantity": "1", "price": "1"}]}]})
            case.merge("material", {"materials": [{"material_number": number}]})
        self.assertEqual([qid for qid, _ in case.questions()].count("fx:KN-4"), 1)


class FirmRouting(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        agent.SITE_ROLES.clear()
        agent.RELEASED.clear()
        agent.TOPIC_SITES.clear()

    tearDown = setUp

    QUESTIONS = [("positions", "p"), ("material:RQ-1", "m"), ("reserve:RQ-2", "r"), ("fx:KN-4", "f"),
                 ("index:IX-2", "i"), ("discount", "d"), ("setup_pool:SP-1", "s"), ("search:tech_release", "t"),
                 ("mailbox", "a")]
    MAIL = ["reserve:RQ-2", "fx:KN-4", "index:IX-2", "discount", "setup_pool:SP-1", "search:tech_release", "mailbox"]

    def test_mail_records_go_to_the_mail_site_named_by_the_brief_only(self):
        agent.SITE_ROLES.update({"erp": "stockroom", "mail": "postbox"})
        self.assertEqual([q for q, _ in questions_for_site("postbox", self.QUESTIONS)], self.MAIL)
        self.assertEqual([q for q, _ in questions_for_site("stockroom", self.QUESTIONS)], ["material:RQ-1"])
        self.assertEqual([q for q, _ in questions_for_site("buyer-portal", self.QUESTIONS)],
                         ["positions", "material:RQ-1"])

    def test_released_mail_records_still_reach_nobody_else(self):
        agent.SITE_ROLES.update({"erp": "stockroom", "mail": "postbox"})
        agent.RELEASED.update(qid for qid, _ in self.QUESTIONS)
        self.assertEqual([q for q, _ in questions_for_site("stockroom", self.QUESTIONS)], ["positions", "material:RQ-1"])

    def test_the_release_skips_owned_mail_records(self):
        agent.SITE_ROLES.update({"erp": "stockroom", "mail": "postbox"})
        case = SimpleNamespace(pending=0, questions=lambda: list(self.QUESTIONS), _bump=lambda: None)
        Team(case, ["stockroom", "postbox"], time.time() + 5).release("postbox", {q for q, _ in self.QUESTIONS})
        self.assertEqual(agent.RELEASED, {"positions", "material:RQ-1"})

    def test_without_a_mail_site_from_the_brief_the_old_routing_applies(self):
        self.assertEqual([q for q, _ in questions_for_site("erp", self.QUESTIONS)], ["material:RQ-1"])
        self.assertEqual([q for q, _ in questions_for_site("mail", self.QUESTIONS)], self.MAIL)
        # one search per topic is the mailbox's work alone
        self.assertNotIn("search:tech_release", [q for q, _ in questions_for_site("buyer-portal", self.QUESTIONS)])
        self.assertIn("reserve:RQ-2", [q for q, _ in questions_for_site("buyer-portal", self.QUESTIONS)])

    def test_only_the_mail_agents_typing_is_noted(self):
        agent.SITE_ROLES.update({"erp": "stockroom", "mail": "postbox"})
        case = casefile.CaseFile("brief", CONTEXT)
        agent.note_search(case, "stockroom", {"do": "fill", "id": 3, "text": "Werkfreigabe"})
        self.assertEqual(case.mail_searches, [])
        agent.note_search(case, "postbox", {"do": "fill", "id": 3, "text": "QK-5150 Werkfreigabe", "enter": True})
        agent.note_search(case, "postbox", {"do": "goto", "url": "/search?q=QK-5150+Kursnotiz&folder=archive"})
        agent.note_search(case, "postbox", {"do": "click", "id": 4})
        self.assertEqual(len(case.mail_searches), 2)
        self.assertEqual(case.searched_topics(), {"tech_release", "fx_fixing"})


class Mailbox:
    """A webmail page with a search field [3]; typing in it changes nothing visible that matters here."""

    def __init__(self):
        self.site_id, self.base_url = "postbox", "http://postbox.test"
        self.page = SimpleNamespace(url="http://postbox.test/inbox", main_frame=SimpleNamespace(evaluate=self._alive))
        self.document, self.document_source = "", ""
        self.typed = ""

    async def _alive(self, script):
        return True

    async def observe(self):
        self.document = (f"url: {self.page.url}\ntitle: Inbox\n# Inbox\n[3] input \"Search\" value=\"{self.typed}\"\n"
                         "No messages match.")
        self.document_source = self.page.url
        return self.document

    async def fill(self, aid, text, enter=False):
        self.typed = text
        return f"typed into [{aid}]"

    def take_events(self):
        return []


async def run_mail_agent(replies):
    agent.SITE_ROLES.update({"mail": "postbox"})
    case = casefile.CaseFile("Bid for tender QK-5150.", CONTEXT)
    case.mailbox = "sales@maker.test"
    asked = []
    counter = iter(range(10 ** 6))

    async def model(messages, **kwargs):
        asked.append(messages[-1]["content"])
        reply = replies.pop(0) if replies else {"do": "done", "summary": "finished"}
        return {"thought": f"step {next(counter)}", "actions": [reply]}

    async def idle(why):
        return None

    team = SimpleNamespace(hook=lambda name: idle)
    with patch.object(llm, "chat_json", model), patch.dict(os.environ, {"AGENT_MAX_STEPS": "20"}):
        outcome = await investigator(case, team, Mailbox(), time.time() + 600).run()
    return case, asked, outcome


class MailDoneGate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        agent.SITE_ROLES.clear()
        agent.RELEASED.clear()
        agent.TOPIC_SITES.clear()

    tearDown = setUp

    DONE = {"do": "done", "summary": "nothing else here"}

    async def test_done_is_refused_while_a_prescribed_topic_was_never_searched(self):
        searches = [{"do": "fill", "id": 3, "text": f"QK-5150 {word}", "enter": True}
                    for word in ("Werkfreigabe", "Kistenpreise", "Kursnotiz", "Rüstkasse")]
        answer = {"do": "answer", "question": "discount", "status": "absent", "note": "no approval in inbox or archive"}
        with patch.dict(os.environ, {"SANITY_CHECKS": "done_gate"}):  # the absent answer is not the coverage gate's test here
            case, asked, outcome = await run_mail_agent([self.DONE] + searches + [answer, self.DONE])
        refusal = asked[1]
        self.assertIn("not finished", refusal)
        self.assertIn("[search:fx_fixing]", refusal)
        self.assertIn("No other agent can find them", refusal)
        self.assertEqual(search_ids(case), [])
        self.assertTrue(outcome["done"])
        self.assertEqual(sum("not finished" in prompt for prompt in asked), 1)

    async def test_the_refusal_is_bounded(self):
        case, asked, outcome = await run_mail_agent([self.DONE] * 6)
        self.assertTrue(outcome["done"])
        self.assertEqual(sum("not finished" in prompt for prompt in asked), DONE_REFUSALS)

    async def test_the_gate_can_be_switched_off(self):
        with patch.dict(os.environ, {"SANITY_CHECKS": "none"}):
            _, asked, outcome = await run_mail_agent([self.DONE])
        self.assertEqual(outcome["steps"], 1)


if __name__ == "__main__":
    unittest.main()

"""The coordinator: a model that sees the whole investigation and hands out work at events, next to the rules.

The open questions (casefile.py) and their routing (agent.questions_for_site) are rules: they cannot anticipate every
way a dataset splits its facts. Eval variant-b run_59d51b28: the ERP agent went idle waiting for requirement values;
they came without a catalogue group, so no material question opened and nothing woke it. Run 72e78b8e: reserve
questions bounced between the mail and the ERP agent and were never searched. Run e27a12ee: the mail agent finished
after the discount and never opened the buyer's quantity-change message.

So at a few EVENTS only (an agent goes idle or is sent idle as stuck; facts were filed while an agent is idle, at most
every DEBOUNCE seconds; every agent is idle and the investigation would end) one model call reads the brief, the case
file, the open questions with their routing and what each agent did, and answers with at most one short concrete task
per agent, plus whether the investigation is complete. A task wakes an idle agent and heads its briefing until it
goes idle again. The model decides what to search and where; code only delivers the task (rule 11: no code-side
crawling). Bounded: MAX_CALLS calls per run, one at a time, at most MAX_EXTENSIONS extensions of the end.

ORCHESTRATOR=1 turns it on, 0 off (then the run behaves exactly as before).
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Callable

import llm

DEFAULT_ON = True
MAX_CALLS = 25  # model calls per run
END_RESERVE = 3  # of them kept for the end checks
MAX_EXTENSIONS = 2  # times the end of the investigation is put off because the coordinator handed out work
DEBOUNCE = 40.0  # seconds between two calls for new facts
MIN_LEFT = 60.0  # investigation seconds that must be left for a call
CALL_LIMIT = 90.0  # seconds one call may take
MAX_TOKENS = 3000
BRIEF_CHARS, STATUS_CHARS, QUESTION_CHARS, TASK_CHARS = 8000, 12000, 300, 400

SYSTEM = """You coordinate research agents that prepare a tender bid. Each agent works ONE website in its own
browser; they file evidence into a shared case file, from which code derives the facts and the open questions. You
see the whole picture: the brief, the case file, the open questions and which agents they are routed to, and what
each agent did. You never browse yourself and you never calculate: you hand out work.

At each event, decide for each agent whether it needs a task now. Give a task when
- facts on file make work possible on a website whose agent is idle or finished (requirement values are on file but
  nobody searched the material master for them; a key is assigned but its record was not searched),
- a question is open but its routed agent said it belongs elsewhere, or nobody searches for it,
- an agent finished while records it should hold are still missing (a message type the brief names that was never
  opened, an amendment or change notice not yet filed), or an agent is stuck: give it a different way.
A task is ONE short concrete instruction for that agent's website: what to search, with which words or values, and
what to file. Use values from the case file. Good: "search the article master by bore 32, stroke 150, mounting X;
file each candidate's status, free stock, lead times and valid price scales"; "search inbox and archive for
'<reference> <subject word>' and file every hit". Never send an agent to another website's records. Give no task to
an agent that is working on the right thing, and do not repeat a task an agent already finished unless you say what
to do differently.

Reply with ONE JSON object:
{"tasks": [{"agent": "<site id>", "task": "<instruction>"}], "investigation_complete": true | false,
 "reason": "<one sentence>"}
"tasks" may be empty. "investigation_complete" is true when every fact the bid rules need is on file or was searched
properly and does not exist; false when work is left (then give the tasks for it)."""


def enabled() -> bool:
    value = os.environ.get("ORCHESTRATOR", "").strip().lower()
    if not value:
        return DEFAULT_ON
    return value not in ("0", "off", "false", "no")


def _thought(reply: str) -> tuple[str, str]:
    """The thought of a stored agent reply and the summary of a done in it."""
    try:
        data = json.loads(reply)
    except (ValueError, TypeError):
        return " ".join(str(reply).split())[:200], ""
    if not isinstance(data, dict):
        return "", ""
    actions = data.get("actions") if isinstance(data.get("actions"), list) else [data.get("actions")]
    done = next((a for a in actions if isinstance(a, dict) and a.get("do") == "done"), None)
    return " ".join(str(data.get("thought") or "").split())[:200], str((done or {}).get("summary") or "")[:200]


class Orchestrator:
    def __init__(self, case, sites: dict[str, dict], brief: str, route: Callable[[str, list], list],
                 deadline: float, chat=None):
        """`sites`: site id -> {"url", "role"}; `brief`: the brief without credentials; `route(site, questions)`:
        the questions routed to that site (agent.questions_for_site); `deadline`: the end of the investigation."""
        self.case, self.sites, self.brief, self.route, self.deadline = case, sites, brief, route, deadline
        self._chat = chat
        self.agents: dict[str, object] = {}  # site id -> worker.Agent, for its last thoughts
        self.state: dict[str, str] = {name: "working" for name in sites}
        self.summary: dict[str, str] = {}  # why it went idle
        self.tasks: dict[str, dict] = {}  # site id -> {"text", "seen"}
        self.history: dict[str, list[str]] = {}  # site id -> finished tasks with the agent's summary
        self.calls = 0
        self.extensions = 0
        self.complete: bool | None = None  # the last call's verdict on the investigation
        self.last_call = 0.0
        self.last_signature: tuple | None = None
        self.lock = asyncio.Lock()
        self.again: str | None = None  # an event that came while a call was running
        self.running: asyncio.Task | None = None
        self.watcher: asyncio.Task | None = None
        # True once the run's token budget is nearly used (agent.py sets it): then no more work is handed out.
        self.over_budget: Callable[[], bool] = lambda: False

    # ---- what the agents see -------------------------------------------------------------------------------------
    def briefing_line(self, name: str) -> str:
        task = self.tasks.get(name)
        if not task:
            return ""
        task["seen"] = True
        return ("TASK FROM THE COORDINATOR (it sees all websites; do this first, it is work for your website even if "
                f"no open question names it, then finish with done):\n{task['text']}")

    def wake(self, name: str) -> str | None:
        """A task this idle agent has not seen yet: delivered once, as the news that wakes it."""
        task = self.tasks.get(name)
        if not task or task["seen"]:
            return None
        task["seen"] = True
        self.state[name] = "working"
        return f"TASK FROM THE COORDINATOR: {task['text']}"

    def undelivered(self) -> set[str]:
        return {name for name, task in self.tasks.items() if not task["seen"]}

    # ---- events ----------------------------------------------------------------------------------------------------
    def went_idle(self, name: str, why: str = "", ask: bool = True) -> None:
        """An agent finished or was sent idle (stuck): its seen task is over, and the coordinator is asked (not when
        it is the last agent to go idle: the end check asks then, confirm_end)."""
        agent = self.agents.get(name)
        summary = str(getattr(agent, "finish_summary", "") or "") or why
        self.state[name] = "stuck" if "repeated the same steps" in summary else "idle"
        self.summary[name] = summary
        task = self.tasks.get(name)
        if task and task["seen"]:
            self.history.setdefault(name, []).append(f"{task['text'][:200]} -> finished: {summary[:150] or 'done'}")
            del self.tasks[name]
        if ask:
            self.request(f"{name} {'is stuck' if self.state[name] == 'stuck' else 'went idle'}"
                         + (f" ({summary[:120]})" if summary else ""))

    def woke(self, name: str) -> None:
        self.state[name] = "working"

    def request(self, event: str) -> None:
        """Ask the coordinator in the background; one call at a time, a later event folded into the next call."""
        if self.running and not self.running.done():
            self.again = event
            return
        try:
            self.running = asyncio.get_running_loop().create_task(self._run(event))
        except RuntimeError:
            pass

    async def _run(self, event: str) -> None:
        while event:
            await self.consult(event)
            event, self.again = self.again, None

    def start_watch(self, finished: asyncio.Event) -> None:
        if self.watcher is None:
            self.watcher = asyncio.get_running_loop().create_task(self._watch(finished))

    async def _watch(self, finished: asyncio.Event) -> None:
        """New facts while an agent is idle: at most one call every DEBOUNCE seconds, once nothing is being read."""
        seen = self.case.version
        while not finished.is_set() and time.time() < self.deadline:
            await self.case.wait_change(seen, 2.0)
            idle = [n for n, s in self.state.items() if s != "working"]
            if (self.case.version != seen and idle and not self.case.pending
                    and time.time() - self.last_call >= DEBOUNCE):
                seen = self.case.version
                self.request(f"new facts on file while {', '.join(sorted(idle))} idle")

    def stop(self) -> None:
        """The investigation is over: no further calls, a running one is dropped."""
        self.deadline = 0.0
        for task in (self.running, self.watcher):
            if task and not task.done():
                task.cancel()

    async def confirm_end(self) -> bool:
        """Every agent is idle: True ends the investigation, False when work was handed out (at most
        MAX_EXTENSIONS times, never too close to the deadline)."""
        if self.extensions >= MAX_EXTENSIONS or self.deadline - time.time() < MIN_LEFT:
            return True
        tasks = await self.consult("every agent is idle: confirm the investigation is complete or hand out the "
                                   "remaining work", final=True)
        if tasks is None or self.complete is True or not any(name in self.undelivered() for name in tasks):
            for name in self.undelivered():  # nobody will be woken for them any more
                del self.tasks[name]
            return True
        self.extensions += 1
        print(f"[orchestrator] investigation extended ({self.extensions}/{MAX_EXTENSIONS})", flush=True)
        return False

    # ---- the call --------------------------------------------------------------------------------------------------
    def _signature(self) -> tuple:
        return (self.case.version, tuple(sorted(self.state.items())), tuple(sorted(self.tasks)))

    async def consult(self, event: str, final: bool = False) -> dict[str, str] | None:
        """One model call for `event`: the tasks it handed out (site id -> task), or None when no call was made."""
        async with self.lock:
            budget = MAX_CALLS if final else MAX_CALLS - END_RESERVE
            left = self.deadline - time.time()
            if self.calls >= budget or left < MIN_LEFT or self.over_budget():
                return None
            if not final and self._signature() == self.last_signature:
                return None  # nothing changed since the last call
            self.calls += 1
            self.last_call = time.time()
            self.last_signature = self._signature()
            chat = self._chat or llm.chat_json
            messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": self.prompt(event)}]
            self.complete = None
            try:  # never raises: a failed call hands out nothing, and the rules go on as without a coordinator
                reply = await asyncio.wait_for(chat(messages, think=True, max_tokens=MAX_TOKENS, label="orchestrator"),
                                               min(CALL_LIMIT, max(5.0, left - 30)))
            except asyncio.TimeoutError:
                reply, why = {}, f"no reply within {min(CALL_LIMIT, max(5.0, left - 30)):.0f} s"
            except Exception as error:  # noqa: BLE001
                reply, why = {}, f"{type(error).__name__}: {str(error)[:120]}"
            else:
                why = ""
            reply = reply if isinstance(reply, dict) else {}
            tasks = self.apply(reply)
            self.complete = reply.get("investigation_complete") if isinstance(reply.get("investigation_complete"), bool) else None
            print(f"[orchestrator] event: {event[:160]} -> tasks: "
                  + ("; ".join(f"{n}: {t[:160]}" for n, t in tasks.items()) or "none")
                  + f" | complete: {self.complete} ({str(reply.get('reason', '') or why)[:160]})"
                  + f" [call {self.calls}/{MAX_CALLS}]", flush=True)
            return tasks

    def apply(self, reply) -> dict[str, str]:
        """The tasks of a reply, for known agents only; each replaces that agent's current task."""
        if not isinstance(reply, dict):
            return {}
        raw = reply.get("tasks")
        raw = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
        names = {name.casefold(): name for name in self.sites}
        given: dict[str, str] = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = names.get(str(item.get("agent") or "").strip().casefold())
            text = " ".join(str(item.get("task") or "").split())[:TASK_CHARS]
            if not name or not text:
                continue
            given[name] = text
            # a working agent reads it at its next turn; an idle one is woken by it (Team.hook)
            self.tasks[name] = {"text": text, "seen": False}
        return given

    def prompt(self, event: str) -> str:
        questions = self.case.questions()
        status = self.case.status() if hasattr(self.case, "status") else ""
        lines = [f"EVENT: {event}", f"INVESTIGATION TIME LEFT: {int(self.deadline - time.time())} s",
                 f"BRIEF (credentials removed)\n{self.brief[:BRIEF_CHARS]}", "",
                 f"CASE FILE\n{status[:STATUS_CHARS]}", ""]
        pending = getattr(self.case, "pending", 0)
        if pending:
            lines.append(f"({pending} filed document(s) are still being read.)")
        lines.append("OPEN QUESTIONS (id: what is missing -> agents it is routed to)")
        for qid, text in questions:
            routed = [name for name in self.sites if any(q == qid for q, _ in self.route(name, [(qid, text)]))]
            lines.append(f"- [{qid}] {' '.join(text.split())[:QUESTION_CHARS]} -> {', '.join(routed) or 'NOBODY'}")
        if not questions:
            lines.append("(none)")
        answers = getattr(self.case, "answers", {}) or {}
        if answers:
            lines.append("CLOSED BY AN AGENT: " + "; ".join(f"{q}: {s} ({n[:80]})" for q, (s, n) in list(answers.items())[-12:]))
        lines += ["", "AGENTS"]
        evidence = getattr(self.case, "evidence", []) or []
        for name, site in self.sites.items():
            role = site.get("role") or "general"
            lines.append(f"## {name} ({site.get('url', '')}; role: {role}; state: {self.state.get(name, 'working')})")
            agent = self.agents.get(name)
            thoughts = [_thought(turn["assistant"])[0] for turn in (getattr(agent, "turns", None) or [])[-3:]]
            thoughts = [t for t in thoughts if t]
            if thoughts:
                lines.append("last thoughts: " + " | ".join(thoughts))
            if self.summary.get(name) and self.state.get(name) != "working":
                lines.append(f"finished with: {self.summary[name]}")
            mine = [e for e in evidence if e.get("agent") == name]
            if mine:
                kinds: dict[str, int] = {}
                for e in mine:
                    kinds[e.get("kind", "?")] = kinds.get(e.get("kind", "?"), 0) + 1
                lines.append("filed: " + ", ".join(f"{k} x{n}" for k, n in kinds.items())
                             + "; latest: " + " | ".join(f"{e.get('kind')}: {str(e.get('summary', ''))[:120]}" for e in mine[-2:]))
            else:
                lines.append("filed: nothing yet")
            if self.tasks.get(name):
                lines.append(f"current task: {self.tasks[name]['text']}")
            for done in self.history.get(name, [])[-2:]:
                lines.append(f"earlier task: {done}")
        return "\n".join(lines)

"""The agent loop: a model reads a browser tab as text, decides what to do next, and acts.

One `Agent` drives one `Tab`. Each turn the model gets its briefing, what its last actions did and the current page,
and answers with a thought and a short list of actions. The loop only carries those out; where to go, what to
search for, which record matters and when the job is finished are the model's calls.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Awaitable, Callable

import llm
from browser_env import Tab

ACTIONS_HELP = """Reply with ONE JSON object: {"thought": "<one or two short sentences: what the page tells you and what you do next>", "actions": [ ... ]}.
The actions run in order. Once an action loads another page the rest of the list is dropped, because the element
ids change with every page: chain actions only while you stay on the page (fill fields, tick boxes, then click).
Elements you can act on carry an id like [12].

Browser actions:
  {"do": "login"}                                  enter this website's credentials in the login form shown and submit it
  {"do": "click", "id": 12}
  {"do": "fill", "id": 12, "text": "...", "enter": false}     type into a field; "enter": true also presses Enter
  {"do": "select", "id": 12, "value": "<an option's value or label>"}
  {"do": "set", "id": 12, "value": true}           tick/untick a checkbox, choose a radio button, or move a slider to a number
  {"do": "goto", "url": "<an address or path on this website that you have seen>"}
  {"do": "back"}    {"do": "reload"}
  {"do": "collect", "id": 12, "max_pages": 10}     [12] is the next-page or load-more control of a list or paged document you want in full: it is followed until the end and all pages come back as one document
  {"do": "fetch", "id": 12}                        download the file behind link [12] (archive, CSV, PDF, text) and read it as a document
  {"do": "wait"}                                   pause two seconds, for a page that is still loading
  {"do": "done", "summary": "<ten words>", "answer": "..."}   you are finished; "answer" only when you were asked for one

Reading the page:
- It is rendered as a screen reader would read it. "(described: ...)" and "(tooltip: ...)" hold text that only
  shows on hover, "[canvas: ...]" what a drawing says, "(in collapsed menu)" an entry of a menu that is closed
  (you can click it all the same), "->" where a link leads, "{data-...}" attributes of a control.
- A "LOCKED AREA" is disabled until you pass the check in front of it. A page can hold several checks, one per
  area, also inside embedded frames further down: after passing one, look for the next LOCKED AREA and its own
  controls. A check whose status already reads as unlocked is done; setting it again changes nothing.
- A "toggle" opens or closes a section. If a section you opened stays empty after you unlocked it, click its toggle
  twice (close, then open) to load it again.
- Several controls can carry the same name while only one of them does the job: tell them apart by where they
  lead and what their attributes say.
- Popups, cookie walls, access checks, error pages and expired sessions happen. Deal with them and carry on;
  after a session expires, log in again. Surveys, tools and help pages lead away from your task.
"""

STEP_TIMEOUT = 45  # seconds for one page read or one browser action: a hung page must not freeze the whole run
FULL_TURNS = 2  # how many past turns stay word for word; older ones keep the reasoning and drop the page text
NAVIGATING = {"click", "goto", "back", "reload", "login", "collect", "fetch"}


class Agent:
    def __init__(self, name: str, tab: Tab, system: str, briefing: Callable[[], str],
                 extra: dict[str, Callable[[dict], Awaitable[str]]] | None = None, deadline: float | None = None,
                 max_steps: int = 80, think: bool = False,
                 idle: Callable[[str], Awaitable[str | None]] | None = None,
                 guard: Callable[[dict], str | None] | None = None):
        """`briefing()` heads every turn. `extra` adds actions: name -> handler(action) -> result text.
        `idle("done")` lets the caller hold a finished agent until there is news for it (returns the news) or
        let it stop (returns None)."""
        self.name, self.tab, self.system, self.briefing = name, tab, system, briefing
        self.extra = extra or {}
        self.deadline = deadline or time.time() + 3600
        self.max_steps, self.think, self.idle = max_steps, think, idle
        self.guard = guard  # a sanity check that may veto a browser action before it runs (sanity.py)
        self.turns: list[dict] = []
        self.held: tuple[str, str] | None = None  # a collected or fetched document, until the agent moves on
        self.steps = 0
        self.started = time.time()

    def document(self) -> tuple[str, str]:
        """What the agent is looking at: the document it collected or fetched, else the page as last read."""
        return self.held or (self.tab.document, self.tab.document_source)

    def log(self, text: str) -> None:
        print(f"[{self.name} {self.steps:02d} t+{time.time() - self.started:.0f}s] {text}", flush=True)

    def _messages(self, user: str) -> list[dict]:
        messages = [{"role": "system", "content": self.system}]
        for index, turn in enumerate(self.turns):
            recent = index >= len(self.turns) - FULL_TURNS
            messages.append({"role": "user", "content": turn["user"] if recent else turn["short"]})
            messages.append({"role": "assistant", "content": turn["assistant"]})
        messages.append({"role": "user", "content": user})
        return messages

    async def _browser(self, action: dict) -> str:
        do, tab = action.get("do"), self.tab
        if do == "login":
            return await tab.login()
        if do == "click":
            return await tab.click(action.get("id"))
        if do == "fill":
            return await tab.fill(action.get("id"), action.get("text", ""), bool(action.get("enter")))
        if do == "select":
            return await tab.select(action.get("id"), action.get("value", ""))
        if do == "set":
            return await tab.set(action.get("id"), action.get("value", True))
        if do == "goto":
            return await tab.goto(action.get("url", ""))
        if do == "back":
            return await tab.back()
        if do == "reload":
            return await tab.reload()
        if do == "collect":
            return await tab.collect(action.get("id"), action.get("max_pages") or 10)
        if do == "fetch":
            return await tab.fetch(action.get("id"))
        return f'unknown action "{do}"'

    async def _alive(self) -> bool:
        try:
            return bool(await self.tab.page.main_frame.evaluate("() => document.querySelectorAll('[data-aid]').length > 0"))
        except Exception:  # noqa: BLE001
            return False

    async def run(self) -> dict:
        results: list[str] = []
        outcome = {"done": False, "summary": "", "answer": None, "steps": 0}
        self.log(f"starting at {self.tab.base_url}")
        if self.tab.page.url in ("", "about:blank"):
            try:
                results.append(await asyncio.wait_for(self.tab.goto(self.tab.base_url + "/"), STEP_TIMEOUT))
            except asyncio.TimeoutError:
                results.append(f"opening {self.tab.base_url} took longer than {STEP_TIMEOUT} s; reload or try again")
        repeats, last_signature, failures = 0, "", 0
        while self.steps < self.max_steps and time.time() < self.deadline:
            self.steps += 1
            clock = time.time()
            try:
                page = await asyncio.wait_for(self.tab.observe(), STEP_TIMEOUT)
            except asyncio.TimeoutError:
                page = f"(the page did not finish loading within {STEP_TIMEOUT} s; reload it or go elsewhere)"
            except Exception as error:  # noqa: BLE001
                page = f"(the page could not be read: {str(error)[:200]})"
            results.extend(self.tab.take_events())
            done_text = "\n".join(f"{n}. {text}" for n, text in enumerate(results, 1)) or "(none yet)"
            left = int(self.deadline - time.time())
            user = (f"{self.briefing()}\n\nTIME LEFT: {left} s\n\nRESULTS OF YOUR LAST ACTIONS\n{done_text}\n\n"
                    f"CURRENT PAGE\n{page}")
            read_s = time.time() - clock
            clock = time.time()
            reply = await llm.chat_json(self._messages(user), think=self.think, label=self.name)
            model_s = time.time() - clock
            clock = time.time()
            actions = reply.get("actions")
            if isinstance(actions, dict):
                actions = [actions]
            if not isinstance(actions, list) or not actions:
                failures += 1
                if failures >= 4:
                    self.log("the model gave no usable actions four times; stopping")
                    break
                results = ['your reply had no "actions" list; reply with {"thought": ..., "actions": [...]}']
                continue
            failures = 0
            thought = str(reply.get("thought", ""))[:300]
            head = page.split("\n", 2)
            short = f"RESULTS OF YOUR LAST ACTIONS\n{done_text[:700]}\n\nPAGE (text dropped)\n" + "\n".join(head[:2])
            self.turns.append({"user": user, "short": short, "assistant": json.dumps(reply, ensure_ascii=False)})
            if os.environ.get("AGENT_TRACE"):  # what the agent saw and answered, one file per turn
                os.makedirs(os.environ["AGENT_TRACE"], exist_ok=True)
                with open(os.path.join(os.environ["AGENT_TRACE"], f"{self.name}_{self.steps:03d}.txt"), "w", encoding="utf-8") as handle:
                    handle.write(user + "\n\n===== REPLY =====\n" + json.dumps(reply, ensure_ascii=False, indent=1))

            signature = json.dumps(actions, sort_keys=True) + self.tab.page.url
            repeats = repeats + 1 if signature == last_signature else 0
            last_signature = signature

            results, finished, moved = [], None, False
            for action in actions[:8]:
                if not isinstance(action, dict):
                    continue
                do = action.get("do")
                if do == "done":
                    finished = action
                    break
                if do == "wait":
                    await asyncio.sleep(2)
                    results.append("waited two seconds")
                    continue
                if do in self.extra:
                    try:
                        results.append(await self.extra[do](action))
                    except Exception as error:  # noqa: BLE001
                        results.append(f"{do} failed: {str(error)[:200]}")
                    continue
                if moved:
                    results.append(f'skipped {json.dumps(action, ensure_ascii=False)[:120]}: the page changed, its ids are stale')
                    continue
                veto = self.guard(action) if self.guard else None
                if veto:
                    results.append(veto)
                    continue
                before = self.tab.page.url
                try:
                    result = await asyncio.wait_for(self._browser(action), STEP_TIMEOUT)
                except asyncio.TimeoutError:
                    result = f"{do} took longer than {STEP_TIMEOUT} s and was stopped; the page may be stuck"
                except Exception as error:  # noqa: BLE001
                    result = f"{do} failed: {str(error)[:200]}"
                results.append(result)
                if do in ("collect", "fetch"):
                    self.held = (self.tab.document, self.tab.document_source)
                elif do in NAVIGATING:
                    self.held = None
                if do in NAVIGATING or self.tab.page.url != before or not await self._alive():
                    moved = True
            self.log(f"(read {read_s:.1f}s, model {model_s:.1f}s, act {time.time() - clock:.1f}s) {thought} | "
                     f"{json.dumps(actions, ensure_ascii=False)[:400]} | " + " ; ".join(r[:160] for r in results))
            if repeats >= 2:
                results.append("You have sent the same actions three times with the same result: they do not work "
                               "here. Read the page again from the top for another way (a further check, a toggle, a "
                               "different link, a search), or finish with done.")
            if finished is not None:
                outcome.update(summary=str(finished.get("summary", "")), answer=finished.get("answer"))
                news = await self.idle("done") if self.idle else None
                if news is None:
                    outcome["done"] = True
                    break
                results.append(news)
        outcome["steps"] = self.steps
        return outcome

"""Branch-and-bound check: replays every agent loop recorded in a sandbox run against a code variant.

    python tuning/replay_loops.py <starter-kit dir> [docs/runs] [--min 15]

For every run log in docs/runs/logs (local only) and every agent whose most frequent thought came back at least
--min times, the agent's recorded replies (thought + actions) are fed, in order, into the Agent class of the given
starter-kit, on a page that never changes. This is the worst case: a model that ignores every hint and repeats
exactly what it did in the sandbox. The script reports after how many turns of the loop the code intervenes:

    idle     an investigator is sent idle (it only comes back when the case file has news for it)
    forced   the agent is forced to give its final answer
    hint     only hints were given; the loop ran to the end of the recording
    none     the code let the whole loop run

Run it once per variant (main, v1, a branch, each checked out as a worktree) to compare them without a sandbox run.
A variant that lets a recorded loop run to the end needs no sandbox run. Holds no scenario values.
"""
from __future__ import annotations

import asyncio
import collections
import importlib
import inspect
import json
import os
import re
import sys
from types import SimpleNamespace
from unittest.mock import patch

TURN = re.compile(r"\[([a-z-]+)(?::[a-z]+)? (\d+) t\+\d+s\] \([^)]*\) (.*)", re.S)
INVESTIGATORS = ("tender-portal", "customer-portal", "erp", "mail")
original_sleep = asyncio.sleep


def parse_actions(raw: str) -> list[dict]:
    """The log cuts the actions JSON at 400 characters: keep the complete actions."""
    raw = raw.strip()
    for end in range(len(raw), 0, -1):
        if raw[end - 1] not in "}]":
            continue
        candidate = raw[:end]
        for suffix in ("", "]", "}]"):
            try:
                value = json.loads(candidate + suffix)
                return [a for a in value if isinstance(a, dict)] if isinstance(value, list) else []
            except ValueError:
                continue
    return []


def recorded_turns(chunks: list[dict]) -> dict[str, list[dict]]:
    turns: dict[str, list[dict]] = collections.defaultdict(list)
    for chunk in chunks:
        match = TURN.match(chunk.get("text", ""))
        if not match:
            continue
        parts = match.group(3).split(" | ")
        thought = parts[0]
        actions = parse_actions(parts[1]) if len(parts) > 1 else []
        turns[match.group(1)].append({"thought": thought, "actions": actions or [{"do": "wait"}]})
    return turns


class FakeTab:
    """A page that never changes, whatever the agent does."""

    def __init__(self, site: str):
        self.base_url = f"https://{site}.test"
        self.site_id = site
        self.document, self.document_source = "", ""
        self.page = SimpleNamespace(url=self.base_url, main_frame=SimpleNamespace(evaluate=self._alive))
        self.view = f"url: {self.base_url}/page\ntitle: Page\n[1] link \"Next\"\n[2] input \"Search\" value=\"\""

    async def _alive(self, script):
        return True

    async def observe(self):
        return self.view

    def take_events(self):
        return []

    def __getattr__(self, name):
        if name not in ("back", "click", "collect", "fetch", "fill", "goto", "login", "reload", "renew", "select", "set",
                        "hover", "press", "scroll", "type", "download", "upload"):
            raise AttributeError(name)

        async def action(*args, **kwargs):
            return f"{name} done"
        return action


async def replay(kit, agent_name: str, turns: list[dict], loop_start: int) -> tuple[str, int]:
    worker = kit
    replies = list(turns)
    seen = {"turn": 0, "event": None, "at": None}

    async def model(messages, **kwargs):
        seen["turn"] += 1
        content = str(messages[-1].get("content", "")) if messages else ""
        if seen["event"] is None and "going in circles" in content.lower() and seen["turn"] - 1 >= loop_start:
            seen["event"], seen["at"] = "hint", seen["turn"] - 1
        if "Stop checking and finish" in content:  # the forced final turn
            return {"do": "done", "summary": "forced", "answer": ""}
        if not replies:
            return {"thought": "end of recording", "actions": [{"do": "done", "summary": "end"}]}
        return replies.pop(0)

    async def idle(why):
        return "The case file has news." if replies else None

    options = {"max_steps": len(turns) + 5}
    accepted = inspect.signature(worker.Agent.__init__).parameters
    if agent_name in INVESTIGATORS:
        options["idle"] = idle
    if agent_name == "courier" and "finish_on_repeat" in accepted:
        options["finish_on_repeat"] = 3
    agent = worker.Agent(agent_name, FakeTab(agent_name), "system", lambda: "job", **options)
    original_log = agent.log

    def log(text):
        if "stuck" in text and seen["turn"] - 1 >= loop_start and seen["event"] in (None, "hint"):
            seen["event"], seen["at"] = "idle", seen["turn"]
        if "forced to finish" in text and seen["event"] in (None, "hint"):
            seen["event"], seen["at"] = "forced", seen["turn"]
        original_log(text)

    agent.log = log

    async def no_sleep(_seconds):
        await original_sleep(0)

    with patch.object(worker.llm, "chat_json", model), patch.object(worker.asyncio, "sleep", no_sleep):
        await agent.run()
    if seen["event"] in ("idle", "forced"):
        return seen["event"], seen["at"] - loop_start
    return seen["event"] or "none", len(turns) - loop_start


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    minimum = int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 15
    kit_dir = os.path.abspath(args[0])
    root = args[1] if len(args) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "runs")
    sys.path.insert(0, kit_dir)
    os.environ.setdefault("OPENAI_API_KEY", "replay")
    import llm  # noqa: F401  (the kit's own model module, patched per replay)
    kit = importlib.import_module("worker")
    kit.print = lambda *a, **k: None  # keep the agents' own logging quiet
    rows = []
    for name in sorted(os.listdir(os.path.join(root, "logs"))):
        turns_by_agent = recorded_turns(json.load(open(os.path.join(root, "logs", name), encoding="utf-8")))
        for agent_name, turns in turns_by_agent.items():
            keys = [" ".join(t["thought"].lower().split())[:70] for t in turns]
            top, count = collections.Counter(keys).most_common(1)[0] if keys else ("", 0)
            if count < minimum:
                continue
            loop_start = keys.index(top)
            loop_length = len(turns) - loop_start
            event, used = asyncio.run(replay(kit, agent_name, turns, loop_start))
            rows.append((name[4:12], agent_name, count, loop_length, event, used))
    print(f"variant: {kit_dir}")
    print("run | agent | repeats | loop turns recorded | intervention | loop turns allowed")
    for row in rows:
        print(" | ".join(str(value) for value in row))
    stopped = [r for r in rows if r[4] in ("idle", "forced")]
    allowed = sum(r[5] for r in rows)
    recorded = sum(r[3] for r in rows)
    print(f"\nstopped {len(stopped)}/{len(rows)} loops; loop turns allowed {allowed} of {recorded} recorded")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

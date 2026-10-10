"""The agents' model client: one JSON chat call to the hosted Qwen, built to survive a busy run.

Every decision the agents take goes through `chat_json`: JSON mode, thinking on or off per call, a cap on how many
calls run at once (the hosted model serves 32 per team across all its runs), retries with backoff and a tolerant
parse of the reply. It never raises: when the last attempt fails it returns {} and the caller decides how to go on
without an answer. `STATS` adds up calls, tokens and seconds; `summary` is the line a run prints at its end.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import sys
import time

from openai import APIStatusError, AsyncOpenAI

MODEL = "qwen"
MAX_CONCURRENT = 16  # the team's limit is 32 across all its runs, and test runs may overlap
ATTEMPTS = 5
CALL_TIMEOUT = 150  # seconds: a model that scaled to zero is slow to answer its first call
WARM_TIMEOUT = 75  # once a call has come back the model is awake; a reply this late is stuck, ask again
MAX_TOKENS_CEILING = 16000  # a reply cut off by its token limit is asked again with twice the room, up to this
PERMANENT = (400, 401, 403, 404, 413, 422)  # asking again rarely helps: one more try, then give up
# The hosted Qwen's simulated prices in USD per million tokens, for the estimate in `summary`.
PRICE_INPUT, PRICE_CACHED, PRICE_OUTPUT = 0.15, 0.016, 0.47
REMINDER = "That reply was not a single JSON object. Answer again with exactly one JSON object and nothing else."

STATS = {"calls": 0, "failed": 0, "prompt_tokens": 0, "cached_tokens": 0, "completion_tokens": 0, "seconds": 0.0}
BY_LABEL: dict[str, list] = {}  # caller kind -> [calls, seconds], to see where a run spends its time
_warm = {"done": False}

_bound: dict = {}  # the client and the gate belong to one event loop; another loop (tests) gets its own


def _session() -> tuple[AsyncOpenAI, asyncio.Semaphore]:
    loop = asyncio.get_running_loop()
    if _bound.get("loop") is not loop:
        client = AsyncOpenAI(base_url=os.environ["QWEN_BASE_URL"], api_key=os.environ["QWEN_API_KEY"],
                             timeout=CALL_TIMEOUT, max_retries=0)  # the retries are ours, so that they are counted
        _bound.update(loop=loop, client=client, gate=asyncio.Semaphore(MAX_CONCURRENT))
    return _bound["client"], _bound["gate"]


def parse_json_object(text: str | None) -> dict | None:
    """The JSON object in a model's reply, or None: a thinking block, code fences and text around it are ignored."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()
    if not text:
        return None
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1).strip())
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        candidates.append(text[start:end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate, strict=False)  # models put raw line breaks into strings
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return parsed
    if start >= 0:  # an object followed by text that has braces of its own
        try:
            parsed, _ = json.JSONDecoder(strict=False).raw_decode(text[start:])
        except ValueError:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def _count(usage) -> None:
    if usage is None:
        return
    STATS["prompt_tokens"] += usage.prompt_tokens or 0
    STATS["completion_tokens"] += usage.completion_tokens or 0
    STATS["cached_tokens"] += getattr(usage.prompt_tokens_details, "cached_tokens", None) or 0


async def chat_json(messages: list[dict], *, think: bool = True, max_tokens: int = 6000, label: str = "") -> dict:
    """One chat call that answers with a JSON object. {} when every attempt failed; it never raises.

    `think` turns the model's reasoning on or off: off is about twice as fast, for the easy steps. `label` names the
    caller in the failure lines on stderr.
    """
    try:
        client, gate = _session()
    except KeyError as missing:
        STATS["failed"] += 1
        print(f"[llm] {label or 'call'}: {missing} is not set, no model to ask", file=sys.stderr)
        return {}
    conversation = messages
    for attempt in range(1, ATTEMPTS + 1):
        permanent = False
        try:
            async with gate:
                STATS["calls"] += 1
                started = time.monotonic()
                try:
                    reply = await asyncio.wait_for(client.chat.completions.create(
                        model=MODEL, messages=conversation, temperature=0, max_tokens=max_tokens,
                        response_format={"type": "json_object"},
                        extra_body={"chat_template_kwargs": {"enable_thinking": think}}),
                        WARM_TIMEOUT if _warm["done"] else CALL_TIMEOUT)
                    _warm["done"] = True
                finally:
                    spent = time.monotonic() - started
                    STATS["seconds"] += spent
                    kind = BY_LABEL.setdefault(label.split(":")[0] if label.startswith("extract") else (label or "call"), [0, 0.0])
                    kind[0] += 1
                    kind[1] += spent
            _count(reply.usage)
            choice = reply.choices[0]
            content = choice.message.content or ""
            parsed = parse_json_object(content)
            if parsed is not None:
                return parsed
            if choice.finish_reason == "length":
                problem = f"the reply was cut off at {max_tokens} tokens"
                max_tokens = min(max_tokens * 2, MAX_TOKENS_CEILING)
            else:
                problem = f"the reply is not a JSON object: {content[:120]!r}"
                conversation = [*messages, {"role": "assistant", "content": content[:2000]},
                                {"role": "user", "content": REMINDER}]
        except asyncio.TimeoutError:
            problem = f"no reply within {WARM_TIMEOUT if _warm['done'] else CALL_TIMEOUT} s"
        except APIStatusError as error:
            problem = f"HTTP {error.status_code}: {str(error)[:200]}"
            permanent = error.status_code in PERMANENT
        except Exception as error:  # the connection, the proxy, a reply without choices
            problem = f"{type(error).__name__}: {str(error)[:200]}"
        STATS["failed"] += 1
        last = attempt == ATTEMPTS or (permanent and attempt >= 2)
        print(f"[llm] {label or 'call'}: attempt {attempt} failed, {problem}" + ("; giving up" if last else ""),
              file=sys.stderr)
        if last:
            break
        await asyncio.sleep(min(2 ** attempt, 20) * random.uniform(0.5, 1))
    return {}


def summary() -> str:
    """The run's model use in one line, with what it costs at the hosted model's simulated prices."""
    fresh = STATS["prompt_tokens"] - STATS["cached_tokens"]
    cost = (fresh * PRICE_INPUT + STATS["cached_tokens"] * PRICE_CACHED
            + STATS["completion_tokens"] * PRICE_OUTPUT) / 1_000_000
    return (f"LLM: {STATS['calls']} calls ({STATS['failed']} failed), {STATS['prompt_tokens']} prompt tokens "
            f"({STATS['cached_tokens']} cached), {STATS['completion_tokens']} completion tokens, "
            f"{STATS['seconds']:.0f} s in calls, about ${cost:.4f}; by caller: "
            + ", ".join(f"{name} {calls}x/{seconds:.0f}s" for name, (calls, seconds) in sorted(BY_LABEL.items())))

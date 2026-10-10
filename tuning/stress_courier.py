"""Stress test of the signing-code courier against a real webmail, before any sandbox run.

The courier (submit.py) is run on its own, with the exact production prompt, N times in a row on the scouting
webmail. An oracle in this harness (plain code, NOT part of the agent) reads the newest code mail directly from the
page source: the highest request number, and the code in it. Every courier answer is compared with it. Sandbox run
a85be021 lost a 100/100 bid because the courier rejected the real code mail; this proves the fix before spending a
run.

Usage (from the repo root, after `atira scout --env` and with `atira models proxy` running):
    uv run --project starter-kit --no-sync python tuning/stress_courier.py <tender reference> [repetitions]
Reads the mailbox login from CHALLENGE_SITE_ACCESS (the site whose id contains "mail"). Holds no scenario values.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "starter-kit"))

from playwright.async_api import async_playwright  # noqa: E402

import submit  # noqa: E402
from browser_env import Tab  # noqa: E402
from worker import ACTIONS_HELP, Agent  # noqa: E402

ZW = re.compile("[​‌‍⁠﻿­]")


async def oracle(tab: Tab, reference: str) -> tuple[int | None, str | None]:
    """Highest request number of the code mails for `reference`, and its code, read with the agent's own page
    renderer but chosen by plain code (the harness knows where to look; the agent does not)."""
    for _ in range(3):  # a cookie or consent page comes first after login
        page = await tab.observe()
        consent = re.search(r"\[(\d+)\][^\n]*(Akzeptier|akzeptier|Zustimm|zustimm|Notwendig|Accept|accept)", page)
        if not consent:
            break
        await tab.click(int(consent.group(1)))
    # unfiltered inbox: a search with more than 20 hits lists nothing on this webmail
    await tab.goto(tab.base_url + "/?folder=inbox&q=")
    text = ZW.sub("", await tab.observe())
    line = r"[^\n]*?"  # within one rendered line
    rows = re.findall(re.escape(reference) + line + r"Anforderung\s*(\d+)" + line + r"->\s*(\S+)", text)
    numbers = [int(n) for n in re.findall(re.escape(reference) + line + r"Anforderung\s*(\d+)", text)]
    if not numbers:
        return None, None
    newest = max(numbers)
    link = next((href for n, href in rows if int(n) == newest), None)
    # the harness may know this site's message path (the agent does not use it): read the newest mail's own page
    await tab.goto(tab.base_url + f"/messages/signing-{newest}")
    body = ZW.sub("", await tab.page.content())
    code = re.search(re.escape(reference) + r"\s*:\s*([0-9A-F]{6,12})", body)
    return newest, code.group(1) if code else None


async def main(reference: str, repetitions: int) -> int:
    sites = json.loads(os.environ["CHALLENGE_SITE_ACCESS"])
    mail = next(site for site in sites if "mail" in site.get("siteId", ""))
    results = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        probe = Tab(await context.new_page(), mail)
        await probe.goto(probe.base_url + "/")
        await probe.login()
        number, expected = await oracle(probe, reference)
        print(f"oracle: newest request {number}, code {expected}")
        for attempt in range(1, repetitions + 1):
            tab = Tab(await context.new_page(), mail)
            system = submit.COURIER.format(site=tab.site_id, url=tab.base_url, reference=reference,
                                           actions=ACTIONS_HELP)
            task = f"Find the signing code (TAN) for tender {reference} that the portal has just sent."
            courier = Agent("courier", tab, system,
                            lambda: f"REQUEST FROM YOUR COLLEAGUE AT THE TENDER PORTAL\n{task}",
                            deadline=time.time() + submit.MAIL_BUDGET, max_steps=submit.COURIER_STEPS,
                            think=submit.COURIER_THINKS, finish_on_repeat=3)
            started = time.time()
            outcome = await courier.run()
            answer = str(outcome.get("answer") or "").strip()
            ok = bool(expected) and answer == expected
            results.append((ok, time.time() - started, outcome.get("steps")))
            print(f"attempt {attempt}: {'OK ' if ok else 'BAD'} answer={answer!r} expected={expected!r} "
                  f"time={time.time() - started:.0f}s steps={outcome.get('steps')}", flush=True)
            await tab.page.close()
        await browser.close()
    good = sum(1 for ok, _, _ in results if ok)
    print(f"courier stress test: {good}/{len(results)} correct, "
          f"mean {sum(t for _, t, _ in results) / max(len(results), 1):.0f}s per attempt")
    return 0 if good == len(results) else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 5)))

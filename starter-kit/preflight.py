"""A conservative, no-model checklist for the tender portal's review page.

The clerk decides when it has reached a review page.  This module only reports
what the accessible page proves.  It tells two things apart:

- blockers: the page shows something wrong (an explicit error, an unfilled
  required control).  The final step is never pressed over these.
- unproven: the page does not show what a review must show (the tender
  reference, every offered position, the calculated total).  A click that
  "worked" proves nothing about what the portal holds, so the final step waits
  for a page that shows them; `submit.py` bounds that wait, because a signed
  bid scores and an unsigned one does not.

It never invents portal-specific field mappings.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from calculator import Bid

ERROR = re.compile(r"\b(error|invalid|failed|missing|fehler|ungültig|pflichtfeld)\b", re.I)
EMPTY_REQUIRED = re.compile(r"^(?=.*\(required\))(?=.*(?:value=\"\"|\[unchecked\])).*$", re.I)


@dataclass(frozen=True)
class Report:
    ready: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    checks: tuple[str, ...]
    unproven: tuple[str, ...] = ()

    def text(self) -> str:
        state = "READY" if self.ready else "BLOCKED"
        lines = [f"PRE-SUBMISSION CHECKLIST: {state}", *[f"- {item}" for item in self.checks]]
        lines += [f"- BLOCKER: {item}" for item in self.blockers]
        lines += [f"- NOT SHOWN: {item}" for item in self.unproven]
        lines += [f"- WARNING: {item}" for item in self.warnings]
        if self.unproven:
            lines.append("This page does not show the whole bid. Open the form's review or summary step that lists "
                         "the reference, every position and the total, compare it with the bid sheet, correct what "
                         "differs, and check again there.")
        return "\n".join(lines)


def _money(value: Decimal) -> set[str]:
    fixed = f"{value:.2f}"
    whole, cents = fixed.split(".")
    return {fixed, fixed.replace(".", ","), f"{int(whole):,}.{cents}", f"{int(whole):,}".replace(",", ".") + "," + cents}


def check(page: str, bid: Bid, reference: str) -> Report:
    """Report review-page evidence without assuming a portal's labels or layout."""
    visible = re.sub(r"\[\d+\] ", "", page)
    lower = visible.lower()
    blockers: list[str] = []
    unproven: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []
    errors = [line.strip() for line in visible.splitlines() if ERROR.search(line)]
    required = [line.strip() for line in visible.splitlines() if EMPTY_REQUIRED.match(line)]
    if errors:
        blockers.append("the portal reports: " + " | ".join(errors[:3])[:500])
    else:
        checks.append("no explicit portal error is visible")
    if required:
        blockers.append("a required control is empty or unchecked: " + " | ".join(required[:3])[:500])
    else:
        checks.append("no empty required control is visible")
    if reference and reference.lower() in lower:
        checks.append(f"tender reference {reference} is visible")
    else:
        unproven.append(f"tender reference {reference} is not visible on this page")
    expected = [line.position for line in bid.lines]
    missing = [position for position in expected if not re.search(rf"(?<![\w.-]){re.escape(position)}(?![\w.-])", visible)]
    if missing:
        unproven.append("offered position(s) not visible in this review: " + ", ".join(missing))
    else:
        checks.append("every offered position is visible")
    if bid.decision == "bid":
        if any(amount in visible for amount in _money(Decimal(bid.total_net))):
            checks.append("calculated total is visible")
        else:
            unproven.append(f"calculated total {Decimal(bid.total_net):.2f} is not visible on this page")
        # A unit price the page does not show is a hint for the clerk's own comparison, not proof of a mistake:
        # a review may list line totals only.
        unpriced = [line.position for line in bid.lines if line.position not in missing and line.unit_price is not None
                    and not any(amount in visible for amount in _money(Decimal(line.unit_price)))]
        if unpriced:
            warnings.append("unit price of the bid sheet not visible for position(s): " + ", ".join(unpriced))
        if bid.omitted:
            warnings.append("the calculator left out position(s): " + ", ".join(bid.omitted)
                            + "; they must not carry invented values")
    return Report(not blockers and not unproven, tuple(blockers), tuple(warnings), tuple(checks), tuple(unproven))

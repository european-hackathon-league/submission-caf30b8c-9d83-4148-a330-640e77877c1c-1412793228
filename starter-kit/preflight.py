"""A conservative, no-model checklist for the tender portal's review page.

The clerk decides when it has reached a review page.  This module only reports
what the accessible page proves and blocks finalisation on explicit errors or
unfilled required controls; it never invents portal-specific field mappings.
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

    def text(self) -> str:
        state = "READY" if self.ready else "BLOCKED"
        lines = [f"PRE-SUBMISSION CHECKLIST: {state}", *[f"- {item}" for item in self.checks]]
        lines += [f"- BLOCKER: {item}" for item in self.blockers]
        lines += [f"- WARNING: {item}" for item in self.warnings]
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
        warnings.append(f"tender reference {reference} is not visible on this page")
    expected = [line.position for line in bid.lines]
    missing = [position for position in expected if not re.search(rf"(?<![\w.-]){re.escape(position)}(?![\w.-])", visible)]
    if missing:
        warnings.append("offered position(s) not visible in this review: " + ", ".join(missing))
    else:
        checks.append("every offered position is visible")
    amounts = _money(Decimal(bid.total_net))
    if any(amount in visible for amount in amounts):
        checks.append("calculated total is visible")
    else:
        warnings.append("calculated total is not visible on this page")
    return Report(not blockers, tuple(blockers), tuple(warnings), tuple(checks))

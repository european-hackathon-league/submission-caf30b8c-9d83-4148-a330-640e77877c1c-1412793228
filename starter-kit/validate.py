"""The last check before the bid is entered: plain code, no model call.

Every field of the answer scores on its own, but a few mistakes cost more than their own field: an extra or duplicate
position costs a whole position's share, a total that is not the sum of the lines loses the total and the arithmetic
points, and a malformed answer is rejected while the clock keeps running. `check` repairs what can be repaired
without guessing (duplicates, positions the tender does not have, a total that does not add up, impossible values)
and reports every change, so the run log shows what would otherwise have been lost.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from calculator import Bid, Line

CENT = Decimal("0.01")


def _cents(value: Decimal) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def check(bid: Bid, tender_positions: set[str] | None = None) -> tuple[Bid, list[str]]:
    """The bid, repaired where that needs no guess, and a list of what was wrong."""
    issues: list[str] = []
    if bid.decision not in ("bid", "no_bid"):
        issues.append(f'decision "{bid.decision}" is neither bid nor no_bid; using bid')
        bid.decision = "bid"
    if not (Decimal(0) <= bid.discount_percent <= Decimal(100)):
        issues.append(f"discount {bid.discount_percent} % is out of range; using 0")
        bid.discount_percent = Decimal(0)

    if bid.decision == "no_bid":
        if bid.lines or bid.total_net != 0:
            issues.append("a no_bid carries no positions and a total of 0; cleared them")
            bid.lines, bid.total_net = [], Decimal(0)
        return bid, issues

    kept: list[Line] = []
    seen: set[str] = set()
    known = {p.strip() for p in tender_positions} if tender_positions else None
    for line in bid.lines:
        key = line.position.strip()
        if key in seen:
            issues.append(f"position {key} appears twice; kept the first (a duplicate costs a position's share)")
            continue
        if known is not None and key not in known:
            issues.append(f"position {key} is not in the tender; dropped it (an extra position costs a share)")
            continue
        problem = _line_problem(line)
        if problem:
            issues.append(f"position {key}: {problem}; omitted it rather than enter a broken line")
            bid.omitted.append(key)
            continue
        seen.add(key)
        kept.append(line)
    bid.lines = kept

    total = _cents(sum((Decimal(line.quantity) * line.unit_price for line in kept), Decimal(0)))
    if _cents(bid.total_net) != total:
        issues.append(f"total {bid.total_net} is not the sum of the lines ({total}); using the sum")
        bid.total_net = total
    return bid, issues


def _line_problem(line: Line) -> str | None:
    if not line.material_number or not str(line.material_number).strip():
        return "no material number"
    if not isinstance(line.quantity, int) or line.quantity <= 0:
        return f"quantity {line.quantity!r} is not a whole number of pieces above 0"
    if line.unit_price is None or line.unit_price < 0:
        return f"unit price {line.unit_price!r} is missing or negative"
    if line.lead_time_weeks is None or line.lead_time_weeks < 0:
        return f"lead time {line.lead_time_weeks!r} is missing or negative"
    for name in ("base_unit_price", "surcharge_per_unit", "packaging_per_unit", "rebate_total"):
        value = getattr(line, name)
        if value is not None and value < 0:
            setattr(line, name, None)  # optional: a blank costs only its own points, a wrong sign may be refused
    return None

"""Local scorer for the Atira RFQ challenge.

Re-implements the published point weights (docs: scoring.md, rule 29 of the brief) so an answer can be
scored in milliseconds against a golden answer, without a sandbox test run.

The golden answer is NOT in this repo: it holds scenario values and lives in the local-only docs/golden/.
This file holds no scenario values and is safe to commit. It is also outside starter-kit/, so it is never
part of the submitted package.

Usage:
    python tuning/scorer.py <answer.json> <golden.json> [--json]

Golden format: the answer schema plus an optional "_checks" object:
    {"withdrawn_qa": {"position": "01.02", "quantity": 40} | null,
     "metal_index":  {"position": "01.03", "field": "surcharge_per_unit"} | null}

Where the published rules are ambiguous, the choice made here is marked ASSUMPTION. Calibrate them against
the breakdown of a real test run (test runs show points per part) and fix them there.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
# Zero-width space, non-joiner, joiner, word joiner, BOM: the sites hide them inside identifiers.
ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF}

# Points per part for a bid case (scoring.md).
DECISION, REFERENCE, DISCOUNT, TOTAL, ARITHMETIC = 5, 5, 5, 5, 5
CHECK_POINTS = 5  # each optional check (withdrawn Q&A quantity, dated metal index), when present
POSITIONS_BASE = 75  # minus the optional checks that are present

# Weights inside one position (sum to 1).
POSITION_FIELDS = {
    "material_number": Decimal("0.20"),
    "quantity": Decimal("0.15"),
    "base_unit_price": Decimal("0.15"),
    "surcharge_per_unit": Decimal("0.10"),
    "packaging_per_unit": Decimal("0.10"),
    "rebate_total": Decimal("0.10"),
    "unit_price": Decimal("0.10"),
    "lead_time_weeks": Decimal("0.10"),
}
MONEY_FIELDS = {"base_unit_price", "surcharge_per_unit", "packaging_per_unit", "rebate_total", "unit_price"}

# No-bid case (scoring.md): decision 75, reference 5, no positions 5, total of 0 15.
NO_BID = {"decision": 75, "reference": 5, "no_positions": 5, "zero_total": 15}


@dataclass
class Score:
    quality: Decimal = Decimal(0)
    parts: dict[str, Decimal] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def add(self, part: str, points: Decimal | int, note: str | None = None) -> None:
        self.parts[part] = self.parts.get(part, Decimal(0)) + Decimal(points)
        self.quality += Decimal(points)
        if note:
            self.notes.append(note)


def money(value) -> Decimal | None:
    """A money value rounded to the cent, or None when blank or unparseable."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def same(field_name: str, got, want) -> bool:
    if got is None or got == "":
        return False  # blank = unanswered, earns nothing
    if field_name in MONEY_FIELDS:
        return money(got) is not None and money(got) == money(want)
    if field_name in {"quantity", "lead_time_weeks"}:
        try:
            return int(got) == int(want)
        except (TypeError, ValueError):
            return False
    return normalise(got) == normalise(want)


def normalise(text) -> str:
    """Strips zero-width characters and surrounding space: the sites inject them into identifiers."""
    return "".join(ch for ch in str(text) if ord(ch) not in ZERO_WIDTH).strip()


def arithmetic_ok(answer: dict) -> bool:
    """ASSUMPTION: 'every position, and a total that is their sum' = total_net equals the half-up rounded
    sum of quantity x unit_price over all positions, and every position has both numbers."""
    positions = answer.get("positions") or []
    try:
        line_sum = sum(
            (Decimal(int(p["quantity"])) * money(p["unit_price"]) for p in positions), Decimal(0)
        ).quantize(CENT, rounding=ROUND_HALF_UP)
    except (KeyError, TypeError, ValueError):
        return False
    return money(answer.get("total_net")) == line_sum


def score(answer: dict, golden: dict) -> Score:
    s = Score()
    if golden.get("decision") == "no_bid":
        return score_no_bid(answer, golden, s)

    s.add("decision", DECISION if answer.get("decision") == "bid" else 0)
    ref_ok = normalise(answer.get("tender_reference", "")) == normalise(golden["tender_reference"])
    s.add("reference", REFERENCE if ref_ok else 0)
    if not ref_ok:
        s.notes.append("NOT ELIGIBLE: wrong tender reference (ranks after every eligible answer)")
    discount_ok = _num_equal(answer.get("discount_percent"), golden.get("discount_percent"))
    s.add("discount", DISCOUNT if discount_ok else 0)
    s.add("total", TOTAL if money(answer.get("total_net")) == money(golden.get("total_net")) else 0)
    s.add("arithmetic", ARITHMETIC if arithmetic_ok(answer) else 0)

    by_position = _index_positions(answer.get("positions") or [], s)
    checks = golden.get("_checks") or {}
    present = [name for name in ("withdrawn_qa", "metal_index") if checks.get(name)]
    golden_positions = golden.get("positions") or []
    golden_by_position = {normalise(p["position"]): p for p in golden_positions}
    for name in present:
        ok = _check_ok(name, checks[name], by_position, golden_by_position)
        s.add(f"check:{name}", CHECK_POINTS if ok else 0)

    share = Decimal(POSITIONS_BASE - CHECK_POINTS * len(present)) / max(len(golden_positions), 1)
    for gp in golden_positions:
        ap = by_position.pop(normalise(gp["position"]), None)
        label = f"position:{gp['position']}"
        if ap is None:
            s.add(label, 0, f"{label} missing or omitted")
            continue
        for name, weight in POSITION_FIELDS.items():
            if same(name, ap.get(name), gp.get(name)):
                s.add(label, share * weight)
            else:
                s.notes.append(f"{label} {name}: got {ap.get(name)!r}, want {gp.get(name)!r}")

    # Extra or duplicate positions cost one position's share each.
    extras = len(by_position) + s.parts.pop("_duplicates", Decimal(0))
    if extras:
        s.add("penalty:extra_positions", -share * extras, f"{int(extras)} extra or duplicate position(s)")
    s.quality = max(s.quality, Decimal(0))
    return s


def score_no_bid(answer: dict, golden: dict, s: Score) -> Score:
    s.add("decision", NO_BID["decision"] if answer.get("decision") == "no_bid" else 0)
    ref_ok = normalise(answer.get("tender_reference", "")) == normalise(golden["tender_reference"])
    s.add("reference", NO_BID["reference"] if ref_ok else 0)
    s.add("no_positions", NO_BID["no_positions"] if not answer.get("positions") else 0)
    s.add("zero_total", NO_BID["zero_total"] if money(answer.get("total_net")) == Decimal("0.00") else 0)
    return s


def _index_positions(positions: list[dict], s: Score) -> dict[str, dict]:
    index: dict[str, dict] = {}
    duplicates = 0
    for p in positions:
        key = normalise(p.get("position", ""))
        if key in index:
            duplicates += 1
        else:
            index[key] = p
    if duplicates:
        s.parts["_duplicates"] = Decimal(duplicates)
    return index


def _check_ok(name: str, spec: dict, by_position: dict[str, dict], golden_by_position: dict[str, dict]) -> bool:
    """ASSUMPTION: the withdrawn-Q&A check compares that position's quantity; the metal-index check compares
    the field named in the golden spec (default surcharge_per_unit) with the golden position's value."""
    key = normalise(spec["position"])
    p = by_position.get(key)
    if p is None:
        return False
    if name == "withdrawn_qa":
        return same("quantity", p.get("quantity"), spec["quantity"])
    field_name = spec.get("field", "surcharge_per_unit")
    want = (golden_by_position.get(key) or {}).get(field_name)
    return want is not None and same(field_name, p.get(field_name), want)


def _num_equal(a, b) -> bool:
    try:
        return Decimal(str(a)) == Decimal(str(b))
    except (InvalidOperation, TypeError):
        return False


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    answer = json.loads(open(argv[1], encoding="utf-8").read())
    golden = json.loads(open(argv[2], encoding="utf-8").read())
    result = score(answer, golden)
    if "--json" in argv:
        print(json.dumps({"quality": str(result.quality.quantize(CENT)),
                          "parts": {k: str(v.quantize(CENT)) for k, v in result.parts.items()},
                          "notes": result.notes}, indent=2))
    else:
        print(f"Quality: {result.quality.quantize(CENT)} / 100")
        for part, points in result.parts.items():
            print(f"  {part:<28} {points.quantize(CENT):>7}")
        for note in result.notes:
            print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

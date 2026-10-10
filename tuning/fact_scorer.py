"""Fact-level scoring: which facts a run collected right, per website, before any arithmetic.

The calculator is proven correct on correct facts, so a run's score is decided by the facts its agents file. This
compares a run's case file (the AGENT_DUMP of a local run) with a golden case file field by field, on the facts the
calculator actually uses, and groups them by the website they come from. It is the cheap "bound" for tuning: a
variant whose facts are worse than the baseline's needs no sandbox run.

Usage:
    python tuning/fact_scorer.py <run casefile dump> <golden casefile json> [--json]

The golden case file ({"context": ..., "dump": ...}) holds scenario values and lives in the local-only docs/ folder.
This file holds none.
"""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "starter-kit"))

from calculator import (active_clarifications, base_price, final_quantities, match_material,  # noqa: E402
                        merged_assignments, resolve_requirements)
from casefile import CaseFile  # noqa: E402

# Which website a fact comes from (the agent responsible for it).
SITE = {"position": "tender-portal", "qa": "tender-portal", "spec": "customer-portal", "material": "erp",
        "price": "erp", "mail": "mail"}


def load_case(dump: dict, context: dict) -> CaseFile:
    """A CaseFile rebuilt from a dump (CaseFile.dump()), with the run's context (reference, date, senders)."""
    case = CaseFile("(offline)", context)
    case.positions = dict(dump.get("positions") or {})
    case.clarifications = dict(dump.get("clarifications") or {})
    case.revisions = dict(dump.get("revisions") or {})
    case.requirements = {tuple(key.split("|", 1)): row for key, row in (dump.get("requirements") or {}).items()}
    case.materials = dict(dump.get("materials") or {})
    case.conditions = {key: {(str(r.get("valid_from")), str(r.get("valid_to"))): r for r in rows}
                       for key, rows in (dump.get("conditions") or {}).items()}
    case.messages = {(str(m.get("sender")), str(m.get("timestamp")), str(m.get("subject"))): m
                     for m in dump.get("messages") or []}
    case.mailbox = dump.get("mailbox")
    return case


def _v(value):
    """A comparable form: Decimals normalised, everything else as text."""
    if isinstance(value, Decimal):
        return str(value.normalize())
    if isinstance(value, (list, tuple)):
        return [_v(item) for item in value]
    return value if value is None or isinstance(value, (int, bool)) else str(value)


def facts_of(case: CaseFile) -> dict[str, object]:
    """The facts the calculator uses, flattened to {"<group>:<key>:<field>": value}."""
    facts = case.inputs()
    answers = active_clarifications(facts.clarifications, case.scenario)
    needs, _waiting = resolve_requirements(facts.requirements, facts.governing, answers, facts.authorities)
    quantities, _unknown = final_quantities(facts.positions, answers, needs)
    assigned, setup_fees = merged_assignments(answers)
    flat: dict[str, object] = {"spec:governing:revision": facts.governing}
    for p in facts.positions:
        flat[f"position:{p.position}:requirement"] = p.requirement_ref
        flat[f"qa:{p.position}:final_quantity"] = quantities.get(p.position)
        for kind, key in sorted((assigned.get(p.position) or {}).items()):
            flat[f"qa:{p.position}:{kind}"] = key
        flat[f"qa:{p.position}:setup_fee"] = _v(setup_fees.get(p.position))
        need = needs.get(p.requirement_ref)
        if need is not None:
            for field in ("bore_mm", "stroke_mm", "pressure_bar", "mounting", "certification"):
                flat[f"spec:{p.requirement_ref}:{field}"] = _v(getattr(need, field, None))
        material = match_material(need, facts.materials) if need is not None else None
        flat[f"material:{p.position}:matched"] = material.number if material else None
        if material is not None:
            for field in ("stock", "stock_lead_weeks", "production_lead_weeks", "carton_size", "allocation_mass_g",
                          "surcharge_mass_g", "index_code"):
                flat[f"material:{material.number}:{field}"] = _v(getattr(material, field))
            if quantities.get(p.position):
                price, _why = base_price(material, quantities[p.position], case.scenario, facts.authorities)
                flat[f"price:{p.position}:base_unit_price"] = _v(price)
    a = facts.authorities
    flat["mail:discount:percent"] = _v(a.discount_percent)
    flat["mail:discount:min_order"] = _v(a.discount_min_order)
    flat["mail:mailbox:address"] = case.mailbox
    for name, mapping in (("clause", a.clauses), ("index_rate", a.index_rates), ("tariff", a.tariffs),
                          ("fx", a.fx), ("pool", a.pools), ("reserve", a.reserves)):
        for key, value in sorted(mapping.items()):
            flat[f"mail:{name}:{key}"] = _v(value)
    for key, commitment in sorted(a.commitments.items()):
        flat[f"mail:commitment:{key}"] = _v([getattr(commitment, f, None) for f in ("material", "max_quantity", "weeks")])
    for key, bands in sorted(a.bonus.items()):
        flat[f"mail:bonus:{key}"] = _v([[b.lower, b.upper, b.percent] for b in bands])
    return flat


def compare(run: dict[str, object], golden: dict[str, object]) -> dict:
    """Per website: facts right, wrong (with both values) and missing, against the golden facts."""
    report: dict[str, dict] = {}
    for key, want in golden.items():
        site = SITE.get(key.split(":", 1)[0], "other")
        entry = report.setdefault(site, {"right": 0, "total": 0, "wrong": [], "missing": []})
        entry["total"] += 1
        got = run.get(key)
        if got == want:
            entry["right"] += 1
        elif got is None:
            entry["missing"].append(key)
        else:
            entry["wrong"].append(f"{key}: got {got!r}, want {want!r}")
    return report


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    golden_file = json.load(open(argv[2], encoding="utf-8"))
    context = golden_file["context"]
    golden = facts_of(load_case(golden_file["dump"], context))
    run = facts_of(load_case(json.load(open(argv[1], encoding="utf-8")), context))
    report = compare(run, golden)
    right = sum(e["right"] for e in report.values())
    total = sum(e["total"] for e in report.values())
    if "--json" in argv:
        print(json.dumps({"right": right, "total": total, "sites": report}, ensure_ascii=False, indent=1))
        return 0
    print(f"Facts right: {right}/{total}")
    for site, e in sorted(report.items()):
        print(f"  {site:<16} {e['right']:>3}/{e['total']:<3}  missing {len(e['missing'])}  wrong {len(e['wrong'])}")
        for line in e["wrong"][:8]:
            print(f"      wrong   {line}")
        for line in e["missing"][:8]:
            print(f"      missing {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

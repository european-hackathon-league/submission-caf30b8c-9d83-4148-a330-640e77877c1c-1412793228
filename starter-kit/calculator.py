"""Deterministic commercial & technical calculation engine for the RFQ-to-Bid challenge.

Implements all 29 bid rules using exact Decimal arithmetic (ROUND_HALF_UP), locale-aware number parsing
(de-DE vs en-US), largest-remainder cent allocation, marginal project bonus bands, and shared stock /
delivery commitment evaluation. Contains zero hardcoded scenario values.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100")
THOUSAND = Decimal("1000")


def round_cents(value: Decimal | int | float | str) -> Decimal:
    """Round half up to the nearest cent (0.01)."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def format_de(value: Decimal | int | float | str, decimals: int = 2) -> str:
    """Format a numeric value in German number format (e.g., 1234,56) without thousands separators."""
    d = Decimal(str(value))
    if decimals == 0 or d == d.to_integral_value():
        if decimals == 0:
            return str(int(d.to_integral_value(rounding=ROUND_HALF_UP)))
    quant = Decimal("10") ** (-decimals) if decimals > 0 else Decimal("1")
    q = d.quantize(quant, rounding=ROUND_HALF_UP)
    return str(q).replace(".", ",")


format_german_decimal = format_de



def parse_locale_decimal(raw: str | int | float | Decimal, locale_hint: str | None = None) -> Decimal:
    """Parse a number string respecting explicit locale hints like '(de-DE)' or '(en-US)'."""
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, (int, float)):
        return Decimal(str(raw))
    text = str(raw).strip()
    if not text:
        return ZERO

    # Detect inline locale tag e.g. "64,853 (en-US)" or "181.429 (de-DE)"
    inline_locale = locale_hint
    m_loc = re.search(r"\((de-DE|en-US)\)", text, re.IGNORECASE)
    if m_loc:
        inline_locale = m_loc.group(1)

    # Extract numeric token
    m_num = re.search(r"[-+]?\d[\d.,\s\u00a0]*", text)
    if not m_num:
        raise ValueError(f"Cannot parse decimal from: {raw!r}")
    token = m_num.group(0).replace(" ", "").replace("\u00a0", "").strip(".,")
    if not token:
        raise ValueError(f"Empty numeric token from: {raw!r}")

    loc = (inline_locale or "").lower()
    if loc == "en-us":
        # In en-US, ',' is thousands separator and '.' is decimal point
        cleaned = token.replace(",", "")
        return Decimal(cleaned)
    if loc == "de-de":
        # In de-DE, '.' is thousands separator and ',' is decimal point
        cleaned = token.replace(".", "").replace(",", ".")
        return Decimal(cleaned)

    # Heuristic when no explicit locale is given
    if "," in token and "." in token:
        if token.rfind(",") > token.rfind("."):
            # 1.234,56 -> de-DE
            cleaned = token.replace(".", "").replace(",", ".")
        else:
            # 1,234.56 -> en-US
            cleaned = token.replace(",", "")
        return Decimal(cleaned)
    if "," in token:
        # Check if comma is decimal separator (e.g. 12,34 or 3,15) vs thousands separator
        parts = token.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2, 4):
            return Decimal(token.replace(",", "."))
        if len(parts) == 2 and len(parts[1]) == 3:
            # Default in German text without en-US tag is comma as decimal unless >1 comma
            return Decimal(token.replace(",", "."))
        return Decimal(token.replace(",", ""))
    if "." in token:
        parts = token.split(".")
        if len(parts) > 2:
            return Decimal(token.replace(".", ""))
        return Decimal(token)
    return Decimal(token)


def parse_timestamp(ts_str: str) -> datetime | None:
    """Parse ISO-8601 or German/portal date strings into UTC datetime."""
    if not ts_str:
        return None
    s = ts_str.strip()
    # 1. Look for ISO-8601 UTC timestamp first: 2027-01-25T08:00:00Z
    m_iso = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z)", s)
    if m_iso:
        iso = m_iso.group(1)
        if len(iso) == 17:  # YYYY-MM-DDTHH:MMZ
            return datetime.strptime(iso, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    # 2. Look for DD.MM.YYYY, HH:MM(:SS) (UTC)
    m_de_dt = re.search(r"(\d{2})\.(\d{2})\.(\d{4})[,\s]+(\d{2}):(\d{2})(?::(\d{2}))?", s)
    if m_de_dt:
        day, month, year, hour, minute, sec = m_de_dt.groups()
        return datetime(
            int(year), int(month), int(day), int(hour), int(minute), int(sec or 0), tzinfo=timezone.utc
        )

    # 3. Look for YYYY-MM-DD
    m_ymd = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m_ymd:
        year, month, day = m_ymd.groups()
        return datetime(int(year), int(month), int(day), tzinfo=timezone.utc)

    # 4. Look for DD.MM.YYYY
    m_de_d = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", s)
    if m_de_d:
        day, month, year = m_de_d.groups()
        return datetime(int(year), int(month), int(day), tzinfo=timezone.utc)

    # 5. Look for slash dates with explicit order: 01/05 (MM/TT) 2027 or 17/01 (TT/MM) 2027
    m_slash = re.search(r"(\d{2})/(\d{2})\s*\((MM/TT|TT/MM|DD/MM)\)\s*[·\s]*(\d{4})", s, re.IGNORECASE)
    if m_slash:
        p1, p2, fmt, year = m_slash.groups()
        if fmt.upper() == "MM/TT":
            month, day = int(p1), int(p2)
        else:
            day, month = int(p1), int(p2)
        return datetime(int(year), month, day, tzinfo=timezone.utc)

    return None


def allocate_cents_largest_remainder(
    total_cents: int, weights: dict[str, Decimal]
) -> dict[str, Decimal]:
    """Allocate `total_cents` across keys proportionally to `weights` using largest remainders.

    Ties are broken by ascending position identifier (key).
    Returns allocated EUR amounts (Decimal with 2 decimal places).
    """
    if not weights or total_cents <= 0:
        return {k: ZERO for k in weights}
    total_weight = sum(weights.values(), Decimal("0"))
    if total_weight <= 0:
        return {k: ZERO for k in weights}

    floors: dict[str, int] = {}
    remainders: dict[str, Decimal] = {}
    for k, w in weights.items():
        exact = (Decimal(total_cents) * w) / total_weight
        fl = int(exact.to_integral_value(rounding=ROUND_FLOOR))
        floors[k] = fl
        remainders[k] = exact - Decimal(fl)

    leftover = total_cents - sum(floors.values())
    # Sort by descending remainder, then ascending position key
    ordered_keys = sorted(weights.keys(), key=lambda k: (-remainders[k], k))
    for k in ordered_keys[: max(0, leftover)]:
        floors[k] += 1

    return {k: (Decimal(c) * CENT).quantize(CENT) for k, c in floors.items()}


def normalize_cert(value: str | None) -> str:
    """Normalize certification strings so 'Keine gefordert', 'Keine', '', '-' match."""
    if not value:
        return "keine"
    v = re.sub(r"\s+", " ", value.strip()).lower()
    if v in ("", "-", "—", "none", "keine", "keine gefordert", "nicht gefordert", "ohne"):
        return "keine"
    return v


def normalize_mounting(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip()).lower()


@dataclass
class TenderPosition:
    position: str
    requirement_ref: str
    original_quantity: int
    unit: str = "Stk"
    description: str = ""


@dataclass
class QAClarification:
    number: str
    timestamp: datetime
    text: str
    withdrawn_number: str | None = None
    # Quantity update: (position, new_quantity, unit)
    quantity_changes: list[tuple[str, int, str]] = field(default_factory=list)
    # Technical amendment: (revision, requirement_ref, attr_name, attr_value)
    tech_amendments: list[tuple[str, str, str, Any]] = field(default_factory=list)
    # Position commercial/operational assignments
    condition_groups: dict[str, str] = field(default_factory=dict)  # pos -> K-xxxx
    packaging_tariffs: dict[str, str] = field(default_factory=dict)  # pos -> VP-xxxx
    delivery_commitments: dict[str, str] = field(default_factory=dict)  # pos -> TZ-xxxx
    setup_pools: dict[str, str] = field(default_factory=dict)  # pos -> RP-xxxx
    bonus_plans: dict[str, str] = field(default_factory=dict)  # pos -> PB-xxxx
    ordinary_setup_fees: dict[str, Decimal] = field(default_factory=dict)  # pos -> EUR


@dataclass
class RequirementSpec:
    req_id: str
    bore_mm: int
    stroke_mm: int
    pressure_bar: int
    mounting: str
    certification: str
    catalogue_group: str
    is_usable_stroke: bool = False
    end_reserve_key: str | None = None
    pieces_per_set: int = 1


@dataclass
class PriceCondition:
    valid_from: datetime
    valid_to: datetime
    currency: str  # "EUR" or "USD"
    fx_key: str | None  # e.g. "FX-xxxx"
    price_unit: int  # e.g. 1 or 100
    locale: str  # "de-DE" or "en-US"
    scales: list[tuple[int, Decimal]] = field(default_factory=list)  # (min_qty, price_per_price_unit)


@dataclass
class ErpMaterial:
    material_number: str
    catalogue_group: str
    status: str  # "01" (active) or "03" (blocked)
    bore_mm: int
    stroke_mm: int
    pressure_bar: int
    mounting: str
    certification: str
    pack_size: int = 1  # Packinhalt (Stück/Karton)
    allocation_weight_g: Decimal = ZERO  # Umlagegewicht (g/Stück)
    surcharge_mass_g: Decimal = ZERO  # Zuschlagsmasse (g/Stück)
    price_index_key: str | None = None  # Preisindex (e.g. MET-xxxx)
    stock_lead_weeks: int = 0
    prod_lead_weeks: int = 0
    free_stock: int = 0
    conditions: list[PriceCondition] = field(default_factory=list)


@dataclass
class DeliveryCommitmentRule:
    key: str
    material_number: str
    lead_weeks: int
    max_pooled_qty: int


@dataclass
class BonusBand:
    lower_eur: Decimal
    upper_eur: Decimal | None  # None means unlimited
    rate_percent: Decimal


@dataclass
class MailRules:
    # Discount approval (latest <= scenario_date from leitung@ for exact ref)
    discount_percent: Decimal = ZERO
    discount_min_order_eur: Decimal = ZERO
    # FX rates: key -> EUR per 1 unit of foreign currency
    fx_rates: dict[str, Decimal] = field(default_factory=dict)
    # Technical end reserves: (revision, reserve_key) -> reserve_mm_per_end (or key -> mm)
    end_reserves: dict[str, tuple[str | None, int]] = field(default_factory=dict)
    # Packaging tariffs: key -> EUR per carton
    packaging_tariffs: dict[str, Decimal] = field(default_factory=dict)
    # Delivery commitments: key -> DeliveryCommitmentRule
    delivery_commitments: dict[str, DeliveryCommitmentRule] = field(default_factory=dict)
    # Setup pools: key -> total pool fee EUR
    setup_pools: dict[str, Decimal] = field(default_factory=dict)
    # Project bonus plans: key -> list of BonusBand
    bonus_plans: dict[str, list[BonusBand]] = field(default_factory=dict)
    # Commercial condition groups: key -> "base_only" | "base_and_surcharge" | "neither"
    condition_clauses: dict[str, str] = field(default_factory=dict)
    # Metal price indices valid on scenario_date: key -> EUR per kg
    metal_indices: dict[str, Decimal] = field(default_factory=dict)


@dataclass
class CalculatedPosition:
    position: str
    material_number: str
    quantity: int
    unit_price: Decimal
    lead_time_weeks: int
    base_unit_price: Decimal
    surcharge_per_unit: Decimal
    packaging_per_unit: Decimal
    rebate_total: Decimal
    # Configurator metadata for site form filling
    bore_mm: int = 0
    stroke_mm: int = 0
    mounting: str = ""
    certification: str = ""

    def to_schema_dict(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "material_number": self.material_number,
            "quantity": int(self.quantity),
            "unit_price": float(self.unit_price),
            "lead_time_weeks": int(self.lead_time_weeks),
            "base_unit_price": float(self.base_unit_price),
            "surcharge_per_unit": float(self.surcharge_per_unit),
            "packaging_per_unit": float(self.packaging_per_unit),
            "rebate_total": float(self.rebate_total),
        }


@dataclass
class BidCalculationResult:
    tender_reference: str
    decision: str  # "bid" or "no_bid"
    currency: str
    discount_percent: Decimal
    positions: list[CalculatedPosition]
    total_net: Decimal
    notes: str = ""

    def to_schema_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {
            "tender_reference": self.tender_reference,
            "decision": self.decision,
            "currency": self.currency,
            "discount_percent": float(self.discount_percent)
            if self.discount_percent != self.discount_percent.to_integral_value()
            else int(self.discount_percent),
            "positions": [p.to_schema_dict() for p in self.positions],
            "total_net": float(self.total_net),
        }
        if self.notes:
            res["notes"] = self.notes[:4000]
        return res


def calculate_bid(
    tender_reference: str,
    scenario_date: datetime,
    governing_revision: str,
    positions: list[TenderPosition],
    clarifications: list[QAClarification],
    requirements: dict[str, RequirementSpec],
    materials: list[ErpMaterial],
    mail_rules: MailRules,
) -> BidCalculationResult:
    """Execute all 29 rules deterministically to produce the complete BidCalculationResult."""
    # Filter clarifications up to scenario_date and sort chronologically (oldest to newest)
    valid_qa = [q for q in clarifications if q.timestamp <= scenario_date]
    valid_qa.sort(key=lambda q: (q.timestamp, q.number))

    # 1. Identify withdrawn Q&A numbers
    withdrawn_numbers: set[str] = set()
    for q in valid_qa:
        if q.withdrawn_number:
            withdrawn_numbers.add(str(q.withdrawn_number).strip())

    active_qa = [q for q in valid_qa if str(q.number).strip() not in withdrawn_numbers]

    # 2. Apply scoped technical amendments to governing revision requirements
    resolved_reqs: dict[str, RequirementSpec] = {
        k: RequirementSpec(
            req_id=v.req_id,
            bore_mm=v.bore_mm,
            stroke_mm=v.stroke_mm,
            pressure_bar=v.pressure_bar,
            mounting=v.mounting,
            certification=v.certification,
            catalogue_group=v.catalogue_group,
            is_usable_stroke=v.is_usable_stroke,
            end_reserve_key=v.end_reserve_key,
            pieces_per_set=v.pieces_per_set,
        )
        for k, v in requirements.items()
    }

    for q in active_qa:
        for rev, req_ref, attr_name, attr_val in q.tech_amendments:
            if rev.strip() == governing_revision.strip() and req_ref in resolved_reqs:
                spec = resolved_reqs[req_ref]
                attr = attr_name.lower()
                if "hub" in attr or "stroke" in attr or "stellweg" in attr:
                    spec.stroke_mm = int(attr_val)
                elif "bohrung" in attr or "bore" in attr:
                    spec.bore_mm = int(attr_val)
                elif "druck" in attr or "pressure" in attr:
                    spec.pressure_bar = int(attr_val)
                elif "befestigung" in attr or "mounting" in attr:
                    spec.mounting = str(attr_val).strip()
                elif "zertifizierung" in attr or "cert" in attr:
                    spec.certification = str(attr_val).strip()

    # 3. Apply technical derivation (nutzbarer Weg + 2 * end reserve from revision-specific Technikfreigabe)
    for req_ref, spec in resolved_reqs.items():
        if spec.is_usable_stroke and spec.end_reserve_key:
            res_entry = mail_rules.end_reserves.get(spec.end_reserve_key)
            if res_entry is not None:
                rev_bound, reserve_mm = res_entry
                if rev_bound is None or rev_bound.strip() == governing_revision.strip():
                    spec.stroke_mm = spec.stroke_mm + 2 * int(reserve_mm)

    # 4. Resolve per-position quantities and Q&A commercial/operational keys
    pos_qty_raw: dict[str, tuple[int, str]] = {
        p.position: (p.original_quantity, p.unit) for p in positions
    }
    pos_cond_group: dict[str, str] = {}
    pos_pack_key: dict[str, str] = {}
    pos_deliv_key: dict[str, str] = {}
    pos_pool_key: dict[str, str] = {}
    pos_bonus_key: dict[str, str] = {}
    pos_ordinary_setup: dict[str, Decimal] = {}

    for q in active_qa:
        for pos_id, new_qty, unit in q.quantity_changes:
            if pos_id in pos_qty_raw:
                orig_unit = pos_qty_raw[pos_id][1]
                pos_qty_raw[pos_id] = (int(new_qty), unit or orig_unit)
        for pos_id, k in q.condition_groups.items():
            pos_cond_group[pos_id] = k
        for pos_id, k in q.packaging_tariffs.items():
            pos_pack_key[pos_id] = k
        for pos_id, k in q.delivery_commitments.items():
            pos_deliv_key[pos_id] = k
        for pos_id, k in q.setup_pools.items():
            pos_pool_key[pos_id] = k
        for pos_id, k in q.bonus_plans.items():
            pos_bonus_key[pos_id] = k
        for pos_id, fee in q.ordinary_setup_fees.items():
            pos_ordinary_setup[pos_id] = Decimal(str(fee))

    # Convert Satz -> Stück using governing specification's pieces_per_set
    final_quantities: dict[str, int] = {}
    for p in positions:
        qty_val, unit_str = pos_qty_raw[p.position]
        spec = resolved_reqs.get(p.requirement_ref)
        mult = 1
        if "satz" in (unit_str or p.unit).lower() and spec and spec.pieces_per_set > 1:
            mult = spec.pieces_per_set
        final_quantities[p.position] = int(qty_val) * mult

    # 5. Match active ERP material for each position
    matched_materials: dict[str, ErpMaterial] = {}
    for p in sorted(positions, key=lambda x: x.position):
        spec = resolved_reqs.get(p.requirement_ref)
        if not spec:
            return BidCalculationResult(
                tender_reference=tender_reference,
                decision="no_bid",
                currency="EUR",
                discount_percent=ZERO,
                positions=[],
                total_net=ZERO,
                notes=f"Missing specification requirement {p.requirement_ref} for position {p.position}",
            )
        candidates = [
            m
            for m in materials
            if m.status == "01"
            and (not spec.catalogue_group or m.catalogue_group == spec.catalogue_group)
            and m.bore_mm == spec.bore_mm
            and m.stroke_mm == spec.stroke_mm
            and m.pressure_bar == spec.pressure_bar
            and normalize_mounting(m.mounting) == normalize_mounting(spec.mounting)
            and normalize_cert(m.certification) == normalize_cert(spec.certification)
        ]
        if not candidates:
            # Check if any active material matches even without catalogue_group filter
            candidates = [
                m
                for m in materials
                if m.status == "01"
                and m.bore_mm == spec.bore_mm
                and m.stroke_mm == spec.stroke_mm
                and m.pressure_bar == spec.pressure_bar
                and normalize_mounting(m.mounting) == normalize_mounting(spec.mounting)
                and normalize_cert(m.certification) == normalize_cert(spec.certification)
            ]
        if not candidates:
            return BidCalculationResult(
                tender_reference=tender_reference,
                decision="no_bid",
                currency="EUR",
                discount_percent=ZERO,
                positions=[],
                total_net=ZERO,
                notes=f"No active matching ERP material for position {p.position} ({p.requirement_ref})",
            )
        matched_materials[p.position] = candidates[0]

    # 6. Compute per-position EUR base_unit_price (valid condition on scenario_date, scale, currency FX, HALF_UP to cents)
    base_unit_prices: dict[str, Decimal] = {}
    for p in positions:
        mat = matched_materials[p.position]
        qty = final_quantities[p.position]
        valid_conds = [
            c for c in mat.conditions if c.valid_from <= scenario_date <= c.valid_to
        ]
        if not valid_conds:
            valid_conds = mat.conditions
        if not valid_conds:
            raise ValueError(f"No price conditions found for material {mat.material_number}")
        cond = valid_conds[0]

        # Select scale with highest min_qty <= qty
        applicable_scales = [s for s in cond.scales if s[0] <= qty]
        if applicable_scales:
            applicable_scales.sort(key=lambda s: s[0], reverse=True)
            scale_price = applicable_scales[0][1]
        else:
            # Fallback to lowest min_qty scale
            cond_scales = sorted(cond.scales, key=lambda s: s[0])
            scale_price = cond_scales[0][1]

        price_per_piece = scale_price / Decimal(cond.price_unit or 1)
        if cond.currency.upper() != "EUR":
            fx_rate = Decimal("1")
            if cond.fx_key and cond.fx_key in mail_rules.fx_rates:
                fx_rate = mail_rules.fx_rates[cond.fx_key]
            elif mail_rules.fx_rates:
                fx_rate = next(iter(mail_rules.fx_rates.values()))
            eur_base = round_cents(price_per_piece * fx_rate)
        else:
            eur_base = round_cents(price_per_piece)
        base_unit_prices[p.position] = eur_base

    # 7. Evaluate conditional director discount approval against undiscounted net order value
    undiscounted_order_value = round_cents(
        sum(
            Decimal(final_quantities[p.position]) * base_unit_prices[p.position]
            for p in positions
        )
    )
    if mail_rules.discount_percent > ZERO:
        if undiscounted_order_value >= mail_rules.discount_min_order_eur:
            approved_discount_pct = mail_rules.discount_percent
        else:
            approved_discount_pct = ZERO
    else:
        approved_discount_pct = ZERO

    # 8. Shared setup pool allocation (by quantity * allocation_weight_g in cents, largest remainders)
    allocated_pool_setup_eur: dict[str, Decimal] = {p.position: ZERO for p in positions}
    pools_to_positions: dict[str, list[str]] = {}
    for pos_id, pool_key in pos_pool_key.items():
        if pool_key and pool_key in mail_rules.setup_pools:
            pools_to_positions.setdefault(pool_key, []).append(pos_id)

    for pool_key, member_positions in pools_to_positions.items():
        pool_fee_eur = mail_rules.setup_pools[pool_key]
        pool_fee_cents = int(round_cents(pool_fee_eur * HUNDRED))
        weights = {
            pos_id: Decimal(final_quantities[pos_id]) * matched_materials[pos_id].allocation_weight_g
            for pos_id in member_positions
        }
        alloc = allocate_cents_largest_remainder(pool_fee_cents, weights)
        for pos_id, amt in alloc.items():
            allocated_pool_setup_eur[pos_id] += amt

    # 9. Project bonus calculation and allocation (marginal bands on eligible undiscounted EUR goods total)
    allocated_bonus_eur: dict[str, Decimal] = {p.position: ZERO for p in positions}
    plans_to_positions: dict[str, list[str]] = {}
    for pos_id, plan_key in pos_bonus_key.items():
        if plan_key and plan_key in mail_rules.bonus_plans:
            plans_to_positions.setdefault(plan_key, []).append(pos_id)

    for plan_key, member_positions in plans_to_positions.items():
        bands = mail_rules.bonus_plans[plan_key]
        line_goods_eur = {
            pos_id: round_cents(Decimal(final_quantities[pos_id]) * base_unit_prices[pos_id])
            for pos_id in member_positions
        }
        eligible_total_eur = sum(line_goods_eur.values(), ZERO)
        raw_bonus_eur = ZERO
        for band in bands:
            if eligible_total_eur > band.lower_eur:
                upper = eligible_total_eur if band.upper_eur is None else min(eligible_total_eur, band.upper_eur)
                portion = max(ZERO, upper - band.lower_eur)
                raw_bonus_eur += portion * (band.rate_percent / HUNDRED)
        total_bonus_eur = round_cents(raw_bonus_eur)
        total_bonus_cents = int(round_cents(total_bonus_eur * HUNDRED))
        # Proportional to line goods values in cents
        weights_cents = {
            pos_id: Decimal(int(round_cents(val * HUNDRED)))
            for pos_id, val in line_goods_eur.items()
        }
        alloc = allocate_cents_largest_remainder(total_bonus_cents, weights_cents)
        for pos_id, amt in alloc.items():
            allocated_bonus_eur[pos_id] += amt

    # 10. Pooled material demand for shared stock & delivery commitments
    pooled_material_demand: dict[str, int] = {}
    for p in positions:
        mat_no = matched_materials[p.position].material_number
        pooled_material_demand[mat_no] = pooled_material_demand.get(mat_no, 0) + final_quantities[p.position]

    # 11. Per-position breakdown, final unit price, and lead time
    calculated_positions: list[CalculatedPosition] = []
    for p in sorted(positions, key=lambda x: x.position):
        pos_id = p.position
        mat = matched_materials[pos_id]
        qty = final_quantities[pos_id]
        qty_dec = Decimal(qty)
        base_eur = base_unit_prices[pos_id]

        # Mass surcharge per unit (unrounded) = (surcharge_mass_g / 1000) * metal_index_rate
        metal_rate = ZERO
        if mat.price_index_key and mat.price_index_key in mail_rules.metal_indices:
            metal_rate = mail_rules.metal_indices[mat.price_index_key]
        elif mail_rules.metal_indices:
            metal_rate = next(iter(mail_rules.metal_indices.values()))
        mass_surcharge_unrounded = (mat.surcharge_mass_g / THOUSAND) * metal_rate

        # Ordinary setup + allocated shared setup
        ordinary_setup_eur = pos_ordinary_setup.get(pos_id, ZERO)
        pool_setup_eur = allocated_pool_setup_eur.get(pos_id, ZERO)
        total_setup_eur = ordinary_setup_eur + pool_setup_eur

        # Reported surcharge_per_unit BEFORE discount (excluding packaging and bonus)
        surcharge_per_unit = round_cents(mass_surcharge_unrounded + (total_setup_eur / qty_dec))

        # Packaging cost
        pack_key = pos_pack_key.get(pos_id)
        tariff_eur = ZERO
        if pack_key and pack_key in mail_rules.packaging_tariffs:
            tariff_eur = mail_rules.packaging_tariffs[pack_key]
        cartons = math.ceil(qty / max(1, mat.pack_size))
        carton_cost_eur = Decimal(cartons) * tariff_eur
        packaging_per_unit = round_cents(carton_cost_eur / qty_dec)

        # Project bonus for the entire position
        rebate_total = round_cents(allocated_bonus_eur.get(pos_id, ZERO))

        # Commercial clause for discount application
        cond_key = pos_cond_group.get(pos_id)
        clause_mode = "base_only"
        if cond_key and cond_key in mail_rules.condition_clauses:
            clause_mode = mail_rules.condition_clauses[cond_key]

        discount_factor = (HUNDRED - approved_discount_pct) / HUNDRED
        if clause_mode == "neither":
            disc_base = base_eur
            disc_mass = mass_surcharge_unrounded
        elif clause_mode == "base_and_surcharge":
            disc_base = base_eur * discount_factor
            disc_mass = mass_surcharge_unrounded * discount_factor
        else:  # "base_only"
            disc_base = base_eur * discount_factor
            disc_mass = mass_surcharge_unrounded

        # Final unit price from unrounded per-piece components, rounded HALF_UP once at the end
        unrounded_unit_price = (
            disc_base
            + disc_mass
            + (ordinary_setup_eur + pool_setup_eur + carton_cost_eur - rebate_total) / qty_dec
        )
        unit_price = round_cents(unrounded_unit_price)

        # Delivery lead time: check commitment first, else shared stock
        pooled_demand = pooled_material_demand[mat.material_number]
        lead_weeks: int | None = None
        deliv_key = pos_deliv_key.get(pos_id)
        if deliv_key and deliv_key in mail_rules.delivery_commitments:
            comm = mail_rules.delivery_commitments[deliv_key]
            if comm.material_number == mat.material_number and pooled_demand <= comm.max_pooled_qty:
                lead_weeks = comm.lead_weeks
        if lead_weeks is None:
            if mat.free_stock >= pooled_demand:
                lead_weeks = mat.stock_lead_weeks
            else:
                lead_weeks = mat.prod_lead_weeks

        cert_val = "Keine" if normalize_cert(mat.certification) == "keine" else mat.certification.strip()
        calculated_positions.append(
            CalculatedPosition(
                position=pos_id,
                material_number=mat.material_number,
                quantity=qty,
                unit_price=unit_price,
                lead_time_weeks=lead_weeks,
                base_unit_price=base_eur,
                surcharge_per_unit=surcharge_per_unit,
                packaging_per_unit=packaging_per_unit,
                rebate_total=rebate_total,
                bore_mm=mat.bore_mm,
                stroke_mm=mat.stroke_mm,
                mounting=mat.mounting.strip(),
                certification=cert_val,
            )
        )

    total_net = round_cents(
        sum(Decimal(cp.quantity) * cp.unit_price for cp in calculated_positions)
    )

    return BidCalculationResult(
        tender_reference=tender_reference,
        decision="bid",
        currency="EUR",
        discount_percent=approved_discount_pct,
        positions=calculated_positions,
        total_net=total_net,
    )


compute_bid = calculate_bid


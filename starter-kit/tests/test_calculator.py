"""Unit tests for the deterministic RFQ-to-Bid calculation and DOM extraction helpers."""
import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculator import (  # noqa: E402
    BonusBand,
    DeliveryCommitmentRule,
    ErpMaterial,
    MailRules,
    PriceCondition,
    QAClarification,
    RequirementSpec,
    TenderPosition,
    allocate_cents_largest_remainder,
    compute_bid,
    parse_locale_decimal,
    parse_timestamp,
)
from dom_helpers import parse_governing_revision, strip_zwc  # noqa: E402


class CalculatorUnitTests(unittest.TestCase):
    def test_locale_decimal_parsing(self):
        self.assertEqual(parse_locale_decimal("2.743,58 (de-DE)"), Decimal("2743.58"))
        self.assertEqual(parse_locale_decimal("2,743.58 (en-US)"), Decimal("2743.58"))
        self.assertEqual(parse_locale_decimal("181,699.48", "en-US"), Decimal("181699.48"))
        self.assertEqual(parse_locale_decimal("85,00", "de-DE"), Decimal("85.00"))

    def test_timestamp_parsing(self):
        self.assertEqual(
            parse_timestamp("25.01.2027, 10:00 · 2027-01-25T08:00:00Z"),
            datetime(2027, 1, 25, 8, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            parse_timestamp("01/05 (MM/TT) 2027"),
            datetime(2027, 1, 5, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            parse_timestamp("17/01 (TT/MM) 2027"),
            datetime(2027, 1, 17, 0, 0, tzinfo=timezone.utc),
        )

    def test_largest_remainder_cent_allocation(self):
        # 100 cents split across equal weights 1, 1, 1 -> 0.34, 0.33, 0.33 (ascending key tie-break)
        alloc = allocate_cents_largest_remainder(
            100,
            {"01.02": Decimal("1"), "01.01": Decimal("1"), "01.03": Decimal("1")},
        )
        self.assertEqual(alloc["01.01"], Decimal("0.34"))
        self.assertEqual(alloc["01.02"], Decimal("0.33"))
        self.assertEqual(alloc["01.03"], Decimal("0.33"))

    def test_governing_revision_selection(self):
        table_text = (
            "Revision R-1001\t01/05 (MM/TT) 2027\tFreigabestand ersetzt\tErstausgabe\n"
            "Revision R-2002\t15/01 (TT/MM) 2027\tFreigabestand gültig\tAktuelle Ausgabe\n"
        )
        scen = datetime(2027, 1, 20, 9, 0, tzinfo=timezone.utc)
        self.assertEqual(parse_governing_revision(table_text, scen), "R-2002")

    def test_compute_bid_end_to_end_synthetic(self):
        scen = datetime(2027, 2, 10, 9, 0, tzinfo=timezone.utc)
        positions = [
            TenderPosition(position="01.01", requirement_ref="A-1", original_quantity=10, unit="Satz"),
        ]
        requirements = {
            "A-1": RequirementSpec(
                req_id="A-1",
                bore_mm=100,
                stroke_mm=380,
                pressure_bar=200,
                mounting="Flansch",
                certification="Keine",
                catalogue_group="GR-0100",
                is_usable_stroke=True,
                end_reserve_key="ER-0100",
                pieces_per_set=2,
            )
        }
        # Q&A 101 changes qty to 12 Satz; Q&A 102 changes qty to 15 Satz; Q&A 103 withdraws 102
        clarifications = [
            QAClarification(
                number="101",
                timestamp=datetime(2027, 2, 5, 10, 0, tzinfo=timezone.utc),
                text="Menge 12 Satz",
                quantity_changes=[("01.01", 12, "Satz")],
                packaging_tariffs={"01.01": "VP-01"},
                delivery_commitments={"01.01": "TZ-01"},
                condition_groups={"01.01": "K-01"},
            ),
            QAClarification(
                number="102",
                timestamp=datetime(2027, 2, 6, 10, 0, tzinfo=timezone.utc),
                text="Menge 15 Satz",
                quantity_changes=[("01.01", 15, "Satz")],
            ),
            QAClarification(
                number="103",
                timestamp=datetime(2027, 2, 7, 10, 0, tzinfo=timezone.utc),
                text="102 zurückgezogen",
                withdrawn_number="102",
            ),
        ]
        # Usable stroke 380 + 2 * 10 = 400 mm nominal stroke; 12 Satz * 2 = 24 pieces
        materials = [
            ErpMaterial(
                material_number="XX-0100",
                catalogue_group="GR-0100",
                status="01",
                bore_mm=100,
                stroke_mm=400,
                pressure_bar=200,
                mounting="Flansch",
                certification="Keine",
                pack_size=10,
                allocation_weight_g=Decimal("1000"),
                surcharge_mass_g=Decimal("2000"),
                price_index_key="MET-01",
                stock_lead_weeks=2,
                prod_lead_weeks=8,
                free_stock=20,
                conditions=[
                    PriceCondition(
                        valid_from=datetime(2027, 1, 1, tzinfo=timezone.utc),
                        valid_to=datetime(2027, 12, 31, tzinfo=timezone.utc),
                        currency="EUR",
                        fx_key=None,
                        price_unit=1,
                        locale="de-DE",
                        scales=[(1, Decimal("1000.00")), (20, Decimal("900.00"))],
                    )
                ],
            )
        ]
        mail_rules = MailRules(
            discount_percent=Decimal("10"),
            discount_min_order_eur=Decimal("1000.00"),
            end_reserves={"ER-0100": ("R-0001", 10)},
            packaging_tariffs={"VP-01": Decimal("12.00")},
            delivery_commitments={
                "TZ-01": DeliveryCommitmentRule(
                    key="TZ-01",
                    material_number="XX-0100",
                    lead_weeks=4,
                    max_pooled_qty=25,
                )
            },
            condition_clauses={"K-01": "base_only"},
            metal_indices={"MET-01": Decimal("3.00")},
        )
        res = compute_bid(
            tender_reference="TR-2027-0001",
            scenario_date=scen,
            governing_revision="R-0001",
            positions=positions,
            requirements=requirements,
            clarifications=clarifications,
            materials=materials,
            mail_rules=mail_rules,
        )
        self.assertEqual(res.decision, "bid")
        self.assertEqual(len(res.positions), 1)
        pos = res.positions[0]
        self.assertEqual(pos.quantity, 24)
        self.assertEqual(pos.lead_time_weeks, 4)  # TZ-01 ceiling 25 >= 24
        self.assertEqual(pos.base_unit_price, Decimal("900.00"))
        self.assertEqual(pos.surcharge_per_unit, Decimal("6.00"))  # 2kg * 3.00 EUR/kg
        self.assertEqual(pos.packaging_per_unit, Decimal("1.50"))  # ceil(24/10)=3 cartons * 12 / 24 = 1.50
        # Discounted base = 810.00 + surcharge 6.00 + packaging 1.50 = 817.50
        self.assertEqual(pos.unit_price, Decimal("817.50"))
        self.assertEqual(res.total_net, Decimal("19620.00"))

    def test_strip_zwc(self):
        self.assertEqual(strip_zwc("A\u200bB\ufeffC"), "ABC")


if __name__ == "__main__":
    unittest.main()

"""The bid rules of the task brief against calculator.py, rule by rule.

Every expected value is worked out by hand from the rule text; the arithmetic stands in the comment next to it and
nothing is read off the module. All references, keys, dates and amounts are invented for these tests.
"""
import json
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculator import (  # noqa: E402
    Authorities, Bid, BonusBand, Clarification, Commitment, Line, Material, Position, PriceCondition, Requirement,
    active_clarifications, allocate_cents, base_price, calculate_bid, final_quantities, match_material, parse_number,
    parse_when, resolve_requirements, round_cents, same_certification, same_text)

UTC = timezone.utc
SCENARIO = datetime(2030, 6, 15, 12, 0, tzinfo=UTC)
REVISION = "REV-2"  # the governing specification revision; REV-1 is superseded


def D(text) -> Decimal:
    return Decimal(str(text))


def june(day: int) -> datetime:
    """A morning in the scenario month: up to the 15th it is before the scenario date, from the 16th after it."""
    return datetime(2030, 6, day, 8, 0, tzinfo=UTC)


def window(first: str, last: str) -> dict:
    """A validity period from two dates, both days included."""
    return {"valid_from": parse_when(first), "valid_to": parse_when(last, end_of_day=True)}


def need(ref: str = "R-1", **changes) -> Requirement:
    return replace(Requirement(ref, bore_mm=11, stroke_mm=100, pressure_bar=22, mounting="flange"), **changes)


def condition(*scales, valid_from=None, valid_to=None, **more) -> PriceCondition:
    """A price condition; each scale is (minimum quantity, price) or just a price from one piece on."""
    pairs = [(scale[0], D(scale[1])) if isinstance(scale, tuple) else (1, D(scale)) for scale in scales]
    return PriceCondition(valid_from, valid_to, scales=pairs, **more)


def material(number: str = "M-1", price: str = "10.00", **changes) -> Material:
    """An active material that meets need() exactly, in ample stock: 1 week from stock, 6 weeks from production."""
    plain = Material(number, active=True, bore_mm=11, stroke_mm=100, pressure_bar=22, mounting="flange",
                     stock=100_000, stock_lead_weeks=1, production_lead_weeks=6, conditions=[condition(price)])
    return replace(plain, **changes)


def pos(number: str = "10", quantity: int = 10, ref: str = "R-1", is_set: bool = False) -> Position:
    return Position(number, ref, quantity, is_set)


def qa(number: str, when: datetime, **content) -> Clarification:
    return Clarification(number, when, **content)


def change(number: str, when: datetime, quantity: int, position: str = "10", is_set=None, **more) -> Clarification:
    """A Q&A answer that sets the quantity of one position."""
    return qa(number, when, quantity_changes=[(position, quantity, is_set)], **more)


def assigned(keys: dict, fees: dict | None = None) -> Clarification:
    """The Q&A answer that assigns keys to positions, with their ordinary setup fees."""
    return qa("Q-KEYS", june(1), assignments=keys, setup_fees={key: D(fee) for key, fee in (fees or {}).items()})


def two_requirements() -> dict:
    """R-1 is met by material(), R-2 by material(stroke_mm=300)."""
    return {"R-1": need(), "R-2": need("R-2", stroke_mm=300)}


def bid(positions, materials, clarifications=(), requirements=None, authorities=None, no_material=None,
        scenario=SCENARIO) -> Bid:
    return calculate_bid("T-0001", scenario, REVISION, list(positions), list(clarifications),
                         requirements or {"R-1": need()}, list(materials), authorities or Authorities(), no_material)


class Case(unittest.TestCase):
    def line(self, result: Bid, number: str = "10") -> Line:
        found = [line for line in result.lines if line.position == number]
        self.assertEqual(len(found), 1, f"position {number} is not priced: {result.decision}, omitted "
                                        f"{result.omitted}, notes {result.notes}")
        return found[0]

    def assertMoney(self, actual, expected: str):
        self.assertIsNotNone(actual, f"expected {expected}, got no value")
        self.assertEqual(Decimal(str(actual)), Decimal(expected))


class Quantity(Case):
    """Rule 1, withdrawn answers, the scenario date and the units."""

    def quantity(self, clarifications=(), tender: int = 7, is_set: bool = False, requirements=None) -> int:
        result = bid([pos(quantity=tender, is_set=is_set)], [material()], clarifications, requirements)
        return self.line(result).quantity

    def test_the_tender_quantity_stands_when_no_answer_changes_it(self):
        self.assertEqual(self.quantity(), 7)

    def test_the_latest_dated_answer_that_changes_the_position_wins(self):
        answers = [change("Q-2", june(5), 30), change("Q-1", june(1), 20)]  # listed newest first on purpose
        self.assertEqual(self.quantity(answers), 30)

    def test_a_later_answer_about_another_position_leaves_this_one_alone(self):
        answers = [change("Q-1", june(1), 20), change("Q-2", june(5), 55, position="20")]
        result = bid([pos("10", 7), pos("20", 9)], [material()], answers)
        self.assertEqual((self.line(result, "10").quantity, self.line(result, "20").quantity), (20, 55))

    def test_an_answer_dated_after_the_scenario_date_is_ignored(self):
        self.assertEqual(self.quantity([change("Q-1", june(1), 20), change("Q-2", june(16), 30)]), 20)
        self.assertEqual(self.quantity([change("Q-2", june(16), 30)]), 7)

    def test_an_answer_dated_exactly_at_the_scenario_date_counts(self):
        self.assertEqual(self.quantity([change("Q-1", SCENARIO, 30)]), 30)

    def test_a_withdrawn_answer_gives_way_to_the_latest_remaining_change(self):
        answers = [change("Q-1", june(1), 20), change("Q-2", june(3), 30), change("Q-3", june(5), 40),
                   qa("Q-4", june(7), withdraws=["Q-3"])]
        self.assertEqual(self.quantity(answers), 30)

    def test_withdrawing_the_only_change_restores_the_tender_quantity(self):
        answers = [change("Q-1", june(1), 20), qa("Q-2", june(5), withdraws=["Q-1"])]
        self.assertEqual(self.quantity(answers), 7)

    def test_a_withdrawing_answer_can_bring_a_change_of_its_own(self):
        answers = [change("Q-1", june(1), 20), change("Q-2", june(5), 25, withdraws=["Q-1"])]
        self.assertEqual(self.quantity(answers), 25)

    def test_a_withdrawal_dated_after_the_scenario_date_withdraws_nothing(self):
        answers = [change("Q-1", june(1), 20), qa("Q-2", june(16), withdraws=["Q-1"])]
        self.assertEqual(self.quantity(answers), 20)

    def test_sets_become_pieces_with_the_pieces_per_set_of_the_specification(self):
        sets_of_six = {"R-1": need(pieces_per_set=6)}
        self.assertEqual(self.quantity(tender=4, is_set=True, requirements=sets_of_six), 24)  # 4 x 6

    def test_an_answer_counts_in_the_unit_of_the_position_unless_it_restates_the_unit(self):
        def sets_of_six():
            return {"R-1": need(pieces_per_set=6)}
        # 5, unit not restated, on a position in sets: 5 x 6 = 30 pieces
        self.assertEqual(self.quantity([change("Q-1", june(1), 5)], 4, True, sets_of_six()), 30)
        # 40 stated in pieces stays 40 pieces
        self.assertEqual(self.quantity([change("Q-1", june(1), 40, is_set=False)], 4, True, sets_of_six()), 40)
        # a position in pieces changed to 5 sets: 30 pieces
        self.assertEqual(self.quantity([change("Q-1", june(1), 5, is_set=True)], 7, False, sets_of_six()), 30)

    def test_active_clarifications_are_the_dated_unwithdrawn_answers_oldest_first(self):
        answers = [qa("Q-4", june(7), withdraws=["Q-2"]), qa("Q-5", june(16), withdraws=["Q-1"]),
                   qa("Q-3", june(5)), qa("Q-1", june(1)), qa("Q-2", june(3))]
        # Q-2 is withdrawn by Q-4; Q-5 comes after the scenario date, so it neither counts nor withdraws Q-1
        self.assertEqual([a.number for a in active_clarifications(answers, SCENARIO)], ["Q-1", "Q-3", "Q-4"])

    def test_final_quantities_are_pieces_per_position_and_name_the_sets_of_unknown_size(self):
        positions = [pos("10", 7), pos("20", 4, "R-2", is_set=True), pos("30", 3, "R-3", is_set=True)]
        requirements = {"R-1": need(), "R-2": need("R-2", pieces_per_set=6), "R-3": need("R-3")}
        answers = active_clarifications([change("Q-1", june(1), 20)], SCENARIO)
        pieces, unknown = final_quantities(positions, answers, requirements)
        self.assertEqual(pieces, {"10": 20, "20": 24})  # the answer's 20; 4 sets x 6
        self.assertEqual(unknown, ["30"])


class RequirementOfTheGoverningRevision(Case):
    """Scoped amendments and the usable-travel derivation, seen through the material they lead to."""

    def chosen(self, clarifications=(), requirements=None, authorities=None, materials=None) -> str:
        materials = materials or [material("M-100"), material("M-150", stroke_mm=150), material("M-300", stroke_mm=300)]
        return self.line(bid([pos()], materials, clarifications, requirements, authorities)).material_number

    def test_without_amendments_the_requirement_stands_as_specified(self):
        self.assertEqual(self.chosen(), "M-100")

    def test_an_amendment_naming_the_governing_revision_and_the_requirement_applies(self):
        answers = [qa("Q-1", june(1), amendments=[(REVISION, "R-1", "stroke", "150")])]
        self.assertEqual(self.chosen(answers), "M-150")

    def test_an_amendment_to_another_revision_does_not_apply(self):
        answers = [qa("Q-1", june(1), amendments=[("REV-1", "R-1", "stroke", "150")])]
        self.assertEqual(self.chosen(answers), "M-100")

    def test_an_amendment_to_another_requirement_does_not_apply(self):
        answers = [qa("Q-1", june(1), amendments=[(REVISION, "R-2", "stroke", "150")])]
        requirements = {"R-1": need(), "R-2": need("R-2")}
        result = bid([pos("10"), pos("20", ref="R-2")], [material("M-100"), material("M-150", stroke_mm=150)],
                     answers, requirements)
        self.assertEqual((self.line(result, "10").material_number, self.line(result, "20").material_number),
                         ("M-100", "M-150"))

    def test_an_amendment_dated_after_the_scenario_date_does_not_apply(self):
        answers = [qa("Q-1", june(16), amendments=[(REVISION, "R-1", "stroke", "150")])]
        self.assertEqual(self.chosen(answers), "M-100")

    def test_the_latest_amendment_wins_per_attribute_and_the_rest_is_inherited(self):
        answers = [qa("Q-2", june(5), amendments=[(REVISION, "R-1", "stroke", "300")]),  # listed newest first
                   qa("Q-1", june(1), amendments=[(REVISION, "R-1", "stroke", "150"),
                                                  (REVISION, "R-1", "pressure", "33")])]
        # stroke 300 from Q-2, pressure 33 from Q-1, bore 11 and the flange from the specification
        materials = [material("M-ORIGINAL"), material("M-OLD-STROKE", stroke_mm=150, pressure_bar=33),
                     material("M-OLD-PRESSURE", stroke_mm=300), material("M-OTHER-BORE", bore_mm=12, stroke_mm=300,
                                                                         pressure_bar=33),
                     material("M-RIGHT", stroke_mm=300, pressure_bar=33)]
        self.assertEqual(self.chosen(answers, materials=materials), "M-RIGHT")

    def test_mounting_and_certification_can_be_amended_too(self):
        answers = [qa("Q-1", june(1), amendments=[(REVISION, "R-1", "mounting", "clevis"),
                                                  (REVISION, "R-1", "certification", "CERT-A")])]
        materials = [material("M-ORIGINAL"), material("M-CLEVIS", mounting="clevis"),
                     material("M-CERTIFIED", certification="CERT-A"),
                     material("M-RIGHT", mounting="clevis", certification="CERT-A")]
        self.assertEqual(self.chosen(answers, materials=materials), "M-RIGHT")

    def test_usable_travel_adds_twice_the_reserve_per_end(self):
        requirements = {"R-1": need(usable_travel=True, reserve_key="RESERVE-A")}
        authorities = Authorities(reserves={"RESERVE-A": (REVISION, 15)})
        materials = [material("M-100"), material("M-115", stroke_mm=115), material("M-130", stroke_mm=130)]
        self.assertEqual(self.chosen((), requirements, authorities, materials), "M-130")  # 100 + 2 x 15

    def test_usable_travel_is_derived_after_the_amendments(self):
        requirements = {"R-1": need(usable_travel=True, reserve_key="RESERVE-A")}
        authorities = Authorities(reserves={"RESERVE-A": (REVISION, 15)})
        answers = [qa("Q-1", june(1), amendments=[(REVISION, "R-1", "stroke", "150")])]
        materials = [material("M-130", stroke_mm=130), material("M-150", stroke_mm=150),
                     material("M-180", stroke_mm=180)]
        self.assertEqual(self.chosen(answers, requirements, authorities, materials), "M-180")  # 150 + 2 x 15

    def test_a_reserve_released_for_another_revision_is_not_added(self):
        requirements = {"R-1": need(usable_travel=True, reserve_key="RESERVE-A")}
        authorities = Authorities(reserves={"RESERVE-A": ("REV-1", 15)})
        materials = [material("M-100"), material("M-130", stroke_mm=130)]
        result = bid([pos()], materials, (), requirements, authorities)
        # the nominal stroke is unknown: neither the bare usable travel nor the other revision's reserve prices it
        self.assertEqual(result.lines, [])
        self.assertEqual(result.omitted, ["10"])

    def test_resolve_requirements_applies_the_amendments_and_then_the_reserve(self):
        requirements = {"R-1": need(usable_travel=True, reserve_key="RESERVE-A"), "R-2": need("R-2")}
        answers = active_clarifications([
            qa("Q-1", june(1), amendments=[(REVISION, "R-1", "stroke", "150"), (REVISION, "R-1", "pressure", "33")]),
            qa("Q-2", june(5), amendments=[("REV-1", "R-2", "stroke", "300")])], SCENARIO)
        resolved, waiting = resolve_requirements(requirements, REVISION, answers,
                                                 Authorities(reserves={"RESERVE-A": (REVISION, 15)}))
        first = resolved["R-1"]
        # 150 + 2 x 15 = 180; the pressure is amended; bore and mounting are inherited
        self.assertEqual((first.bore_mm, first.stroke_mm, first.pressure_bar, first.mounting), (11, 180, 33, "flange"))
        self.assertEqual(resolved["R-2"].stroke_mm, 100)  # its amendment names the superseded revision
        self.assertEqual(waiting, {})

    def test_resolve_requirements_names_the_requirement_that_waits_for_its_reserve(self):
        requirements = {"R-1": need(usable_travel=True, reserve_key="RESERVE-A"), "R-2": need("R-2")}
        _, waiting = resolve_requirements(requirements, REVISION, [], Authorities())
        self.assertEqual(list(waiting), ["R-1"])


class MaterialSelection(Case):
    """Rule 3: an active material equal in bore, stroke, pressure, mounting and certification; else no_bid."""

    def certified(self) -> dict:
        return {"R-1": need(certification="CERT-A")}

    def near_misses(self) -> list[Material]:
        return [material("M-BORE", bore_mm=12, certification="CERT-A"),
                material("M-STROKE", stroke_mm=101, certification="CERT-A"),
                material("M-PRESSURE", pressure_bar=23, certification="CERT-A"),
                material("M-MOUNTING", mounting="clevis", certification="CERT-A"),
                material("M-OTHER-CERTIFICATE", certification="CERT-B"),
                material("M-NO-CERTIFICATE")]

    def test_the_material_equal_in_every_attribute_is_selected(self):
        materials = self.near_misses() + [material("M-EXACT", certification="CERT-A")]
        self.assertEqual(self.line(bid([pos()], materials, requirements=self.certified())).material_number, "M-EXACT")

    def test_a_material_that_differs_in_one_attribute_does_not_match(self):
        for candidate in self.near_misses():
            with self.subTest(candidate.number):
                result = bid([pos()], [candidate], requirements=self.certified(), no_material={"R-1"})
                self.assertEqual((result.decision, result.lines), ("no_bid", []))

    def test_a_blocked_material_does_not_qualify(self):
        materials = [material("M-BLOCKED", active=False), material("M-ACTIVE")]
        self.assertEqual(self.line(bid([pos()], materials)).material_number, "M-ACTIVE")

    def test_only_a_blocked_match_is_a_no_bid_with_no_positions_and_a_total_of_zero(self):
        result = bid([pos()], [material("M-BLOCKED", active=False)], no_material={"R-1"})
        self.assertEqual((result.decision, result.lines), ("no_bid", []))
        self.assertMoney(result.total_net, "0")

    def test_one_position_without_a_material_makes_the_whole_answer_a_no_bid(self):
        for missing, flagged in (("R-1", "10"), ("R-2", "20")):  # whichever position it is
            with self.subTest(position=flagged):
                kept = material("M-2", stroke_mm=300) if missing == "R-1" else material("M-1")
                result = bid([pos("10"), pos("20", ref="R-2")], [kept], requirements=two_requirements(),
                             no_material={missing})
                self.assertEqual((result.decision, result.lines), ("no_bid", []))
                self.assertMoney(result.total_net, "0")

    def test_a_no_bid_keeps_an_unconditional_approval(self):
        result = bid([pos()], [], authorities=Authorities(discount_percent=D(5)), no_material={"R-1"})
        self.assertEqual((result.decision, result.discount_percent), ("no_bid", D(5)))

    def test_a_no_bid_with_a_conditional_approval_has_zero_percent(self):
        authorities = Authorities(discount_percent=D(5), discount_min_order=D("1.00"))
        result = bid([pos()], [], authorities=authorities, no_material={"R-1"})
        self.assertEqual((result.decision, result.discount_percent), ("no_bid", D(0)))

    def test_match_material_returns_the_active_exact_match_or_none(self):
        exact = material("M-EXACT", certification="CERT-A")
        wanted = need(certification="CERT-A")
        self.assertIs(match_material(wanted, self.near_misses() + [exact]), exact)
        self.assertIsNone(match_material(wanted, self.near_misses()))
        self.assertIsNone(match_material(wanted, [replace(exact, active=False)]))
        self.assertIsNone(match_material(wanted, []))

    def test_match_material_prefers_the_catalogue_group_the_requirement_names(self):
        elsewhere, grouped = material("M-ELSEWHERE", catalogue_group="CAT-B"), material("M-GROUPED",
                                                                                         catalogue_group="CAT-A")
        self.assertIs(match_material(need(catalogue_group="CAT-A"), [elsewhere, grouped]), grouped)

    def test_no_certificate_is_the_same_however_it_is_written(self):
        for a, b in ((None, ""), (None, "none"), ("-", None), ("CERT-A", "cert-a")):
            self.assertTrue(same_certification(a, b), (a, b))
        for a, b in (("CERT-A", None), ("CERT-A", "CERT-B"), ("none", "CERT-A")):
            self.assertFalse(same_certification(a, b), (a, b))

    def test_same_text_ignores_case_and_spacing_only(self):
        self.assertTrue(same_text("Flange ", "flange"))
        self.assertFalse(same_text("flange", "clevis"))
        self.assertFalse(same_text("flange", None))


class PartialBids(Case):
    """Positions that lack evidence are left out; the others keep their values. A no_bid needs the requirement
    named in `no_material`."""

    def assertFirstPositionAsIfAlone(self, result: Bid, omitted: list[str]):
        self.assertEqual(result.decision, "bid")
        self.assertEqual(result.omitted, omitted)
        self.assertEqual([line.position for line in result.lines], ["10"])
        line = self.line(result)
        # 10 pieces at 10.00, from stock in 1 week: 100.00
        self.assertEqual((line.material_number, line.quantity, line.lead_time_weeks), ("M-1", 10, 1))
        self.assertMoney(line.unit_price, "10.00")
        self.assertMoney(result.total_net, "100.00")

    def test_a_position_whose_material_was_not_found_is_omitted(self):
        result = bid([pos("10"), pos("20", 5, "R-2")], [material()], requirements=two_requirements())
        self.assertFirstPositionAsIfAlone(result, ["20"])

    def test_the_same_position_is_a_no_bid_once_its_requirement_is_named_in_no_material(self):
        result = bid([pos("10"), pos("20", 5, "R-2")], [material()], requirements=two_requirements(),
                     no_material={"R-2"})
        self.assertEqual((result.decision, result.lines), ("no_bid", []))

    def test_a_no_bid_wins_over_an_omission(self):
        requirements = {**two_requirements(), "R-3": need("R-3", stroke_mm=None)}
        result = bid([pos("10", ref="R-3"), pos("20", ref="R-2"), pos("30")], [material()],
                     requirements=requirements, no_material={"R-2"})
        self.assertEqual((result.decision, result.lines), ("no_bid", []))

    def test_a_position_with_an_unknown_requirement_is_omitted(self):
        result = bid([pos("10"), pos("20", 5, "R-9")], [material()])
        self.assertFirstPositionAsIfAlone(result, ["20"])

    def test_a_position_whose_requirement_lacks_an_attribute_is_omitted(self):
        requirements = {"R-1": need(), "R-2": need("R-2", stroke_mm=None)}
        result = bid([pos("10"), pos("20", 5, "R-2")], [material()], requirements=requirements)
        self.assertFirstPositionAsIfAlone(result, ["20"])

    def test_a_position_in_sets_of_unknown_size_is_omitted(self):
        result = bid([pos("10"), pos("20", 5, is_set=True)], [material()])
        self.assertFirstPositionAsIfAlone(result, ["20"])

    def test_a_position_without_a_price_valid_on_the_scenario_date_is_omitted(self):
        expired = material("M-2", stroke_mm=300, conditions=[condition("10.00", **window("2030-01-01", "2030-05-31"))])
        result = bid([pos("10"), pos("20", 5, "R-2")], [material(), expired], requirements=two_requirements())
        self.assertFirstPositionAsIfAlone(result, ["20"])

    def test_omitted_positions_are_left_out_of_the_answer(self):
        result = bid([pos("10"), pos("20", 5, "R-2")], [material()], requirements=two_requirements())
        self.assertEqual([entry["position"] for entry in result.answer()["positions"]], ["10"])


class BasePrice(Case):
    """Rule 4 and the currency rule: the valid condition, the highest scale reached, the price unit, the FX."""

    def price(self, conditions, quantity: int = 10, authorities=None, scenario=SCENARIO):
        return base_price(material(conditions=conditions), quantity, scenario, authorities or Authorities())[0]

    def test_the_condition_valid_on_the_scenario_date_is_the_one_used(self):
        conditions = [condition("99.00", **window("2030-01-01", "2030-05-31")),
                      condition("10.00", **window("2030-06-01", "2030-06-30")),
                      condition("55.00", **window("2030-07-01", "2030-12-31"))]
        self.assertMoney(self.price(conditions), "10.00")
        self.assertMoney(self.line(bid([pos()], [material(conditions=conditions)])).base_unit_price, "10.00")

    def test_validity_includes_its_first_day(self):
        self.assertMoney(self.price([condition("10.00", **window("2030-06-15", "2030-12-31"))]), "10.00")
        starts_now = condition("10.00", valid_from=SCENARIO, valid_to=parse_when("2030-12-31", end_of_day=True))
        self.assertMoney(self.price([starts_now]), "10.00")

    def test_validity_includes_its_last_day(self):
        self.assertMoney(self.price([condition("10.00", **window("2030-01-01", "2030-06-15"))]), "10.00")
        ends_now = condition("10.00", valid_from=parse_when("2030-01-01"), valid_to=SCENARIO)
        self.assertMoney(self.price([ends_now]), "10.00")

    def test_a_condition_that_ended_yesterday_or_starts_tomorrow_is_not_valid(self):
        self.assertIsNone(self.price([condition("10.00", **window("2030-01-01", "2030-06-14"))]))
        self.assertIsNone(self.price([condition("10.00", **window("2030-06-16", "2030-12-31"))]))

    def test_the_scale_with_the_highest_minimum_quantity_reached_is_chosen(self):
        scales = [condition((50, "8.00"), (1, "10.00"), (10, "9.00"))]  # not listed in order
        for quantity, expected in ((1, "10.00"), (9, "10.00"), (10, "9.00"), (49, "9.00"), (50, "8.00"),
                                   (500, "8.00")):
            with self.subTest(quantity=quantity):
                self.assertMoney(self.price(scales, quantity), expected)

    def test_scales_are_reached_per_position_not_by_the_sum_for_the_material(self):
        scaled = material(conditions=[condition((1, "10.00"), (10, "9.00"), (50, "8.00"))])
        result = bid([pos("10", 30), pos("20", 30)], [scaled])  # 60 together, 30 each
        self.assertMoney(self.line(result, "10").base_unit_price, "9.00")
        self.assertMoney(self.line(result, "20").base_unit_price, "9.00")

    def test_scales_are_reached_in_final_pieces(self):
        scaled = material(conditions=[condition((1, "10.00"), (20, "9.00"))])
        result = bid([pos("10", 4, is_set=True)], [scaled], requirements={"R-1": need(pieces_per_set=6)})
        self.assertMoney(self.line(result).base_unit_price, "9.00")  # 4 sets x 6 = 24 pieces reach the scale of 20

    def test_the_price_unit_is_normalised_to_one_piece(self):
        self.assertMoney(self.price([condition("1250.00", price_unit=100)]), "12.50")  # 1250.00 / 100

    def test_a_foreign_price_is_converted_and_rounded_half_up_to_the_cent(self):
        foreign = [condition("12.50", currency="XTS", fx_key="FX-A")]
        authorities = Authorities(fx={"FX-A": D("0.85"), "FX-B": D("2")})
        self.assertMoney(self.price(foreign, authorities=authorities), "10.63")  # 12.50 x 0.85 = 10.625

    def test_the_price_unit_is_normalised_before_the_conversion(self):
        foreign = [condition((1, "1300.00"), (10, "1250.00"), currency="XTS", fx_key="FX-A", price_unit=100)]
        authorities = Authorities(fx={"FX-A": D("0.85")})
        self.assertMoney(self.price(foreign, 10, authorities), "10.63")  # 1250.00 / 100 = 12.50; x 0.85 = 10.625

    def test_a_price_in_eur_needs_no_fixing(self):
        self.assertMoney(self.price([condition("12.50", currency="EUR")]), "12.50")

    def test_the_converted_price_is_what_every_later_step_uses(self):
        foreign = material(conditions=[condition("12.50", currency="XTS", fx_key="FX-A")])
        authorities = Authorities(fx={"FX-A": D("0.85")}, discount_percent=D(10), discount_min_order=D("31.89"))
        result = bid([pos("10", 3)], [foreign], authorities=authorities)
        line = self.line(result)
        self.assertMoney(line.base_unit_price, "10.63")
        # the threshold sees 3 x 10.63 = 31.89 and is met (3 x 10.625 = 31.875 would round to 31.88 and miss it)
        self.assertEqual(result.discount_percent, D(10))
        self.assertMoney(line.unit_price, "9.57")  # 10.63 x 0.9 = 9.567 (10.625 x 0.9 = 9.5625 would give 9.56)
        self.assertMoney(result.total_net, "28.71")  # 3 x 9.57

    def test_base_price_says_why_there_is_none(self):
        price, why = base_price(material(conditions=[]), 10, SCENARIO, Authorities())
        self.assertIsNone(price)
        self.assertTrue(why)


class Discount(Case):
    """Rules 4 and 5 and the conditional approval."""

    def two_positions(self, authorities, clarifications=(), first=None) -> Bid:
        # 10 x 10.00 = 100.00 and 5 x 20.00 = 100.00: goods worth 200.00 before any discount
        materials = [first or material("M-1"), material("M-2", "20.00", stroke_mm=300)]
        return bid([pos("10", 10), pos("20", 5, "R-2")], materials, clarifications, two_requirements(), authorities)

    def test_without_an_approval_the_discount_is_zero_percent(self):
        result = bid([pos()], [material()])
        self.assertEqual(result.discount_percent, D(0))
        self.assertMoney(self.line(result).unit_price, "10.00")

    def test_the_approved_percentage_comes_off_the_scale_price(self):
        result = bid([pos()], [material()], authorities=Authorities(discount_percent=D(10)))
        self.assertEqual(result.discount_percent, D(10))
        self.assertMoney(self.line(result).unit_price, "9.00")  # 10.00 x 0.9
        self.assertMoney(self.line(result).base_unit_price, "10.00")  # the reported base is the price before it
        self.assertMoney(result.total_net, "90.00")

    def test_the_discounted_price_is_rounded_half_up(self):
        result = bid([pos()], [material(price="10.05")], authorities=Authorities(discount_percent=D(10)))
        self.assertMoney(self.line(result).unit_price, "9.05")  # 10.05 x 0.9 = 9.045

    def test_a_fractional_percentage(self):
        result = bid([pos()], [material()], authorities=Authorities(discount_percent=D("2.5")))
        self.assertMoney(self.line(result).unit_price, "9.75")  # 10.00 x 0.975

    def test_a_conditional_approval_applies_when_the_order_value_equals_its_minimum(self):
        result = self.two_positions(Authorities(discount_percent=D(10), discount_min_order=D("200.00")))
        self.assertEqual(result.discount_percent, D(10))
        self.assertMoney(self.line(result, "10").unit_price, "9.00")
        self.assertMoney(self.line(result, "20").unit_price, "18.00")
        self.assertMoney(result.total_net, "180.00")  # 10 x 9.00 + 5 x 18.00

    def test_one_cent_below_its_minimum_the_discount_is_zero_percent(self):
        result = self.two_positions(Authorities(discount_percent=D(10), discount_min_order=D("200.01")))
        self.assertEqual(result.discount_percent, D(0))
        self.assertMoney(self.line(result, "10").unit_price, "10.00")
        self.assertMoney(self.line(result, "20").unit_price, "20.00")
        self.assertMoney(result.total_net, "200.00")

    def test_the_minimum_is_compared_with_the_value_before_the_discount(self):
        # 200.00 undiscounted meets 190.00; the discounted 180.00 would not
        result = self.two_positions(Authorities(discount_percent=D(10), discount_min_order=D("190.00")))
        self.assertEqual(result.discount_percent, D(10))

    def test_surcharges_setup_fees_and_packaging_do_not_count_towards_the_minimum(self):
        loaded = material("M-1", index_code="INDEX-A", surcharge_mass_g=D(100), carton_size=10)
        authorities = Authorities(discount_percent=D(10), discount_min_order=D("200.01"),
                                  index_rates={"INDEX-A": D("0.01")}, tariffs={"TARIFF-A": D("4.00")})
        keys = assigned({"10": {"packaging_tariff": "TARIFF-A"}}, fees={"10": "50.00"})
        result = self.two_positions(authorities, [keys], first=loaded)
        self.assertEqual(result.discount_percent, D(0))  # still 200.00 of goods against 200.01
        # 10.00 + 100 g x 0.01 + (50.00 setup + 1 carton x 4.00) / 10 = 10.00 + 1.00 + 5.40
        self.assertMoney(self.line(result, "10").unit_price, "16.40")
        self.assertMoney(self.line(result, "20").unit_price, "20.00")

    def test_the_minimum_is_compared_with_final_pieces(self):
        authorities = Authorities(discount_percent=D(10), discount_min_order=D("240.00"))
        result = bid([pos("10", 4, is_set=True)], [material()], requirements={"R-1": need(pieces_per_set=6)},
                     authorities=authorities)
        self.assertEqual(result.discount_percent, D(10))  # 4 sets x 6 x 10.00 = 240.00


class CommercialClauses(Case):
    """What the approved discount applies to: by default the base, by condition group base and surcharge or
    nothing, and never the setup fee."""

    # one piece costs 100.00 and carries 100 g x 0.10 = 10.00 of mass surcharge; the approval is 10 %
    def priced(self, groups: dict, fees: dict | None = None, positions=None) -> Bid:
        authorities = Authorities(discount_percent=D(10), index_rates={"INDEX-A": D("0.10")},
                                  clauses={"GROUP-BOTH": "base_and_surcharge", "GROUP-NONE": "none",
                                           "GROUP-BASE": "base_only"})
        keys = assigned({number: {"condition_group": group} for number, group in groups.items()}, fees)
        metal = material(price="100.00", index_code="INDEX-A", surcharge_mass_g=D(100))
        return bid(positions or [pos()], [metal], [keys], authorities=authorities)

    def test_without_a_group_only_the_base_is_discounted(self):
        self.assertMoney(self.line(self.priced({})).unit_price, "100.00")  # 90.00 + 10.00

    def test_a_base_only_group_does_the_same(self):
        self.assertMoney(self.line(self.priced({"10": "GROUP-BASE"})).unit_price, "100.00")

    def test_a_group_can_extend_the_discount_to_the_mass_surcharge(self):
        self.assertMoney(self.line(self.priced({"10": "GROUP-BOTH"})).unit_price, "99.00")  # 90.00 + 9.00

    def test_a_group_can_exclude_the_discount_altogether(self):
        self.assertMoney(self.line(self.priced({"10": "GROUP-NONE"})).unit_price, "110.00")  # 100.00 + 10.00

    def test_setup_fees_are_never_discounted(self):
        result = self.priced({"10": "GROUP-BOTH"}, fees={"10": "50.00"})
        self.assertMoney(self.line(result).unit_price, "104.00")  # 90.00 + 9.00 + 50.00 / 10

    def test_the_group_decides_even_between_two_positions_with_the_same_material(self):
        result = self.priced({"10": "GROUP-NONE"}, positions=[pos("10"), pos("20")])
        self.assertEqual(self.line(result, "10").material_number, self.line(result, "20").material_number)
        self.assertMoney(self.line(result, "10").unit_price, "110.00")
        self.assertMoney(self.line(result, "20").unit_price, "100.00")

    def test_a_group_changes_what_is_discounted_not_the_approved_percentage(self):
        self.assertEqual(self.priced({"10": "GROUP-NONE"}).discount_percent, D(10))

    def test_the_reported_surcharge_is_the_one_before_the_discount(self):
        self.assertMoney(self.line(self.priced({"10": "GROUP-BOTH"})).surcharge_per_unit, "10.00")


class MassSurcharge(Case):
    """The metal index rate times the material's surcharge mass, per piece."""

    def metal(self, **changes) -> Material:
        return material(index_code="INDEX-A", surcharge_mass_g=D(250), **changes)

    def rates(self, **more) -> Authorities:
        return Authorities(index_rates={"INDEX-A": D("0.02"), "INDEX-B": D("9")}, **more)

    def test_the_rate_times_the_surcharge_mass_is_added_per_piece(self):
        line = self.line(bid([pos()], [self.metal()], authorities=self.rates()))
        self.assertMoney(line.surcharge_per_unit, "5.00")  # 250 g x 0.02
        self.assertMoney(line.unit_price, "15.00")  # 10.00 + 5.00

    def test_it_uses_the_surcharge_mass_not_the_allocation_mass(self):
        line = self.line(bid([pos()], [self.metal(allocation_mass_g=D(900))], authorities=self.rates()))
        self.assertMoney(line.surcharge_per_unit, "5.00")

    def test_a_material_without_an_index_has_a_known_surcharge_of_zero(self):
        line = self.line(bid([pos()], [material()], authorities=self.rates()))
        self.assertMoney(line.surcharge_per_unit, "0.00")

    def test_the_reported_surcharge_is_rounded_half_up(self):
        fine = material(index_code="INDEX-A", surcharge_mass_g=D("6.25"))
        line = self.line(bid([pos()], [fine], authorities=self.rates()))
        self.assertMoney(line.surcharge_per_unit, "0.13")  # 6.25 g x 0.02 = 0.125

    def test_the_reported_surcharge_leaves_out_packaging_and_bonus(self):
        authorities = self.rates(tariffs={"TARIFF-A": D("4.00")}, bonus={"BONUS-A": [BonusBand(D(0), None, D(1))]})
        keys = assigned({"10": {"packaging_tariff": "TARIFF-A", "project_bonus": "BONUS-A"}})
        line = self.line(bid([pos()], [self.metal(carton_size=10)], [keys], authorities=authorities))
        self.assertMoney(line.surcharge_per_unit, "5.00")
        # 10.00 + 5.00 + (1 carton x 4.00 - 1 % of 100.00) / 10 = 15.00 + 0.30
        self.assertMoney(line.unit_price, "15.30")


class Packaging(Case):
    """ceil(final pieces / carton size) cartons per position at the assigned tariff; never discounted."""

    def packed(self, quantities: dict, authorities=None, requirements=None, sets=False, tariff="4.00") -> Bid:
        authorities = authorities or Authorities()
        authorities.tariffs = {"TARIFF-A": D(tariff), "TARIFF-B": D("99.00")}
        keys = assigned({number: {"packaging_tariff": "TARIFF-A"} for number in quantities})
        positions = [pos(number, quantity, is_set=sets) for number, quantity in quantities.items()]
        return bid(positions, [material(carton_size=10)], [keys], requirements, authorities)

    def test_a_started_carton_is_charged_in_full(self):
        result = self.packed({"10": 25})
        line = self.line(result)
        self.assertMoney(line.packaging_per_unit, "0.48")  # ceil(25 / 10) = 3 cartons x 4.00 = 12.00; / 25
        self.assertMoney(line.unit_price, "10.48")
        self.assertMoney(result.total_net, "262.00")  # 25 x 10.48

    def test_carton_rounding_never_changes_the_bid_quantity(self):
        self.assertEqual(self.line(self.packed({"10": 25})).quantity, 25)

    def test_full_cartons_are_not_rounded_up_further(self):
        self.assertMoney(self.line(self.packed({"10": 20})).packaging_per_unit, "0.40")  # 2 cartons x 4.00 / 20

    def test_one_piece_over_takes_another_carton(self):
        result = self.packed({"10": 21})
        self.assertMoney(self.line(result).packaging_per_unit, "0.57")  # 3 cartons x 4.00 / 21 = 0.5714...
        self.assertMoney(self.line(result).unit_price, "10.57")
        self.assertMoney(result.total_net, "221.97")  # 21 x 10.57

    def test_packaging_is_not_discounted(self):
        result = self.packed({"10": 25}, Authorities(discount_percent=D(10)))
        self.assertMoney(self.line(result).unit_price, "9.48")  # 9.00 + 0.48
        self.assertMoney(self.line(result).packaging_per_unit, "0.48")

    def test_cartons_are_counted_for_each_position_on_its_own(self):
        result = self.packed({"10": 5, "20": 5})  # one carton each, not one carton for the ten pieces together
        self.assertMoney(self.line(result, "10").packaging_per_unit, "0.80")  # 4.00 / 5
        self.assertMoney(self.line(result, "20").packaging_per_unit, "0.80")

    def test_cartons_are_counted_in_final_pieces(self):
        result = self.packed({"10": 4}, requirements={"R-1": need(pieces_per_set=6)}, sets=True)
        self.assertMoney(self.line(result).packaging_per_unit, "0.50")  # 24 pieces: 3 cartons x 4.00 / 24

    def test_the_reported_packaging_is_rounded_half_up(self):
        self.assertMoney(self.line(self.packed({"10": 2}, tariff="0.25")).packaging_per_unit, "0.13")  # 0.25 / 2

    def test_a_position_without_a_tariff_has_a_known_packaging_of_zero(self):
        line = self.line(bid([pos()], [material(carton_size=10)],
                             authorities=Authorities(tariffs={"TARIFF-A": D("4.00")})))
        self.assertMoney(line.packaging_per_unit, "0.00")
        self.assertMoney(line.unit_price, "10.00")


class SharedSetup(Case):
    """The pool fee, allocated by quantity x allocation mass, on top of the ordinary setup fee."""

    def pooled(self, authorities=None, fees=None, method="largest_remainder") -> Bid:
        # position 10: 10 pieces x 300 g = 3000; position 20: 20 pieces x 100 g = 2000; position 30 is no member
        # 100.00 x 3000 / 5000 = 60.00 and 100.00 x 2000 / 5000 = 40.00
        authorities = authorities or Authorities()
        authorities.pools = {"POOL-A": (D("100.00"), method), "POOL-B": (D("999.00"), method)}
        materials = [material("M-1", allocation_mass_g=D(300), surcharge_mass_g=D(100)),
                     material("M-2", allocation_mass_g=D(100), surcharge_mass_g=D(100), stroke_mm=300)]
        keys = assigned({"10": {"setup_pool": "POOL-A"}, "20": {"setup_pool": "POOL-A"}}, fees)
        return bid([pos("10", 10), pos("20", 20, "R-2"), pos("30", 10)], materials, [keys], two_requirements(),
                   authorities)

    def test_the_fee_is_shared_by_quantity_times_allocation_mass(self):
        result = self.pooled()
        self.assertMoney(self.line(result, "10").unit_price, "16.00")  # 10.00 + 60.00 / 10
        self.assertMoney(self.line(result, "20").unit_price, "12.00")  # 10.00 + 40.00 / 20
        self.assertMoney(result.total_net, "500.00")  # 160.00 + 240.00 + 100.00: the goods plus the whole fee

    def test_a_position_outside_the_pool_carries_none_of_it(self):
        self.assertMoney(self.line(self.pooled(), "30").unit_price, "10.00")
        self.assertMoney(self.line(self.pooled(), "30").surcharge_per_unit, "0.00")

    def test_the_share_is_added_to_the_ordinary_setup_fee(self):
        result = self.pooled(fees={"10": "30.00"})
        self.assertMoney(self.line(result, "10").unit_price, "19.00")  # 10.00 + (30.00 + 60.00) / 10

    def test_setup_is_not_discounted(self):
        result = self.pooled(Authorities(discount_percent=D(10)), fees={"10": "30.00"})
        self.assertMoney(self.line(result, "10").unit_price, "18.00")  # 9.00 + (30.00 + 60.00) / 10

    def test_the_reported_surcharge_carries_the_setup_per_piece_before_discount(self):
        # the brief reports setup with the surcharge: surcharge_per_unit leaves out only packaging and bonus
        result = self.pooled(Authorities(discount_percent=D(10)), fees={"10": "30.00"})
        self.assertMoney(self.line(result, "10").surcharge_per_unit, "9.00")  # (30.00 + 60.00) / 10
        self.assertMoney(self.line(result, "20").surcharge_per_unit, "2.00")  # 40.00 / 20

    def test_the_weights_count_final_pieces(self):
        # position 10 is 2 sets of 5: 10 pieces x 300 g = 3000 against 20 x 100 g = 2000, so 60.00 / 40.00 again
        # (weighing the 2 sets as 2 would give 600 against 2000)
        materials = [material("M-1", allocation_mass_g=D(300)),
                     material("M-2", allocation_mass_g=D(100), stroke_mm=300)]
        requirements = {"R-1": need(pieces_per_set=5), "R-2": need("R-2", stroke_mm=300)}
        keys = assigned({"10": {"setup_pool": "POOL-A"}, "20": {"setup_pool": "POOL-A"}})
        result = bid([pos("10", 2, is_set=True), pos("20", 20, "R-2")], materials, [keys], requirements,
                     Authorities(pools={"POOL-A": (D("100.00"), "largest_remainder")}))
        self.assertMoney(self.line(result, "10").unit_price, "16.00")  # 10.00 + 60.00 / 10
        self.assertMoney(self.line(result, "20").unit_price, "12.00")  # 10.00 + 40.00 / 20

    def three_equal_members(self, method: str) -> list[Decimal]:
        # 100.00 over three equal weights is 33.33 each and one cent over
        keys = assigned({number: {"setup_pool": "POOL-A"} for number in ("10", "20", "30")})
        authorities = Authorities(pools={"POOL-A": (D("100.00"), method)})
        result = bid([pos("10", 1), pos("20", 1), pos("30", 1)], [material(allocation_mass_g=D(100))], [keys],
                     authorities=authorities)
        return [self.line(result, number).unit_price for number in ("10", "20", "30")]

    def test_the_odd_cent_goes_by_largest_remainder_with_ties_to_the_lower_position(self):
        self.assertEqual(self.three_equal_members("largest_remainder"), [D("43.34"), D("43.33"), D("43.33")])

    def test_the_odd_cent_goes_where_the_rule_of_the_pool_sends_it(self):
        self.assertEqual(self.three_equal_members("remainder_to_last"), [D("43.33"), D("43.33"), D("43.34")])
        self.assertEqual(self.three_equal_members("remainder_to_first"), [D("43.34"), D("43.33"), D("43.33")])


class ProjectBonus(Case):
    """Marginal bands on the eligible undiscounted goods value, allocated by largest remainders."""

    BANDS = [BonusBand(D(0), D(1000), D(1)), BonusBand(D(1000), None, D(2))]  # 1 % up to 1000.00, 2 % above

    def rebated(self, quantities: dict, members=None, price="100.00", authorities=None, bands=None, groups=None) -> Bid:
        authorities = authorities or Authorities()
        authorities.bonus = {"BONUS-A": bands or self.BANDS, "BONUS-B": [BonusBand(D(0), None, D(50))]}
        keys = {number: {"project_bonus": "BONUS-A"} for number in (quantities if members is None else members)}
        for number, group in (groups or {}).items():
            keys.setdefault(number, {})["condition_group"] = group
        positions = [pos(number, quantity) for number, quantity in quantities.items()]
        return bid(positions, [material(price=price)], [assigned(keys)], authorities=authorities)

    def rebates(self, result: Bid) -> dict:
        return {line.position: line.rebate_total for line in result.lines}

    def test_each_band_applies_to_its_own_portion_only(self):
        # goods 10 x 100.00 = 1000.00 and 20 x 100.00 = 2000.00: eligible 3000.00
        # credit 1000.00 x 1 % + 2000.00 x 2 % = 50.00 (a flat 2 % would be 60.00)
        # shares 50.00 / 3 = 16.666... and 33.333...: floors 16.66 + 33.33, the cent goes to the larger remainder
        result = self.rebated({"10": 10, "20": 20})
        self.assertEqual(self.rebates(result), {"10": D("16.67"), "20": D("33.33")})

    def test_the_rebate_is_for_the_whole_position_and_comes_off_per_piece(self):
        result = self.rebated({"10": 10, "20": 20})
        self.assertMoney(self.line(result, "10").unit_price, "98.33")  # 100.00 - 16.67 / 10 = 98.333
        self.assertMoney(self.line(result, "20").unit_price, "98.33")  # 100.00 - 33.33 / 20 = 98.3335
        self.assertMoney(result.total_net, "2949.90")  # 10 x 98.33 + 20 x 98.33

    def test_three_bands(self):
        bands = [BonusBand(D(0), D(1000), D(1)), BonusBand(D(1000), D(2000), D(2)), BonusBand(D(2000), None, D(3))]
        result = self.rebated({"10": 25}, bands=bands)  # 2500.00: 10.00 + 20.00 + 500.00 x 3 % = 45.00
        self.assertEqual(self.rebates(result), {"10": D("45.00")})
        self.assertMoney(self.line(result).unit_price, "98.20")  # 100.00 - 45.00 / 25

    def test_the_aggregate_credit_is_rounded_half_up(self):
        result = self.rebated({"10": 1}, price="100.50")  # 100.50 x 1 % = 1.005
        self.assertEqual(self.rebates(result), {"10": D("1.01")})

    def test_a_tie_goes_to_the_lower_position(self):
        result = self.rebated({"10": 1, "20": 1}, price="50.50")  # 101.00 x 1 % = 1.01: 0.505 each
        self.assertEqual(self.rebates(result), {"10": D("0.51"), "20": D("0.50")})

    def test_a_tie_between_shares_of_different_size_still_goes_to_the_lower_position(self):
        # goods 2000.00, 500.00 and 500.00: eligible 3000.00, credit 10.00 + 40.00 = 50.00
        # shares 33.33 1/3, 8.33 1/3 and 8.33 1/3 cents-wise: floors 33.33 + 8.33 + 8.33 = 49.99, one cent left,
        # and all three remainders are exactly a third of a cent, so the lowest position gets it
        result = self.rebated({"10": 20, "20": 5, "30": 5})
        self.assertEqual(self.rebates(result), {"10": D("33.34"), "20": D("8.33"), "30": D("8.33")})

    def test_position_numbers_ascend_as_numbers(self):
        # the same tie between positions 2 and 10: position 2 comes first, though "10" sorts before "2" as text
        result = self.rebated({"2": 1, "10": 1}, price="50.50")
        self.assertEqual(self.rebates(result), {"2": D("0.51"), "10": D("0.50")})

    def test_a_position_outside_the_plan_has_a_rebate_of_zero_and_adds_nothing_to_the_eligible_total(self):
        result = self.rebated({"10": 10, "20": 20}, members=["10"])
        self.assertEqual(self.rebates(result), {"10": D("10.00"), "20": D("0.00")})  # 1000.00 x 1 %
        self.assertMoney(self.line(result, "10").unit_price, "99.00")  # 100.00 - 10.00 / 10
        self.assertMoney(self.line(result, "20").unit_price, "100.00")

    def test_the_bonus_is_worked_out_on_undiscounted_goods_whatever_the_clause(self):
        for group, unit_price in ((None, "88.33"), ("GROUP-NONE", "98.33")):  # 90.00 or 100.00, less 16.67 / 10
            with self.subTest(group=group):
                authorities = Authorities(discount_percent=D(10), clauses={"GROUP-NONE": "none"})
                result = self.rebated({"10": 10, "20": 20}, authorities=authorities,
                                      groups={"10": group} if group else None)
                self.assertEqual(self.rebates(result), {"10": D("16.67"), "20": D("33.33")})
                self.assertMoney(self.line(result, "10").unit_price, unit_price)


class FinalPrice(Case):
    """Clause-discounted base + clause-discounted surcharge + (setup + pool share + cartons - bonus) / pieces,
    rounded half up once; the total adds quantity x rounded unit price."""

    def test_every_component_together(self):
        materials = [material("M-1", "100.00", index_code="INDEX-A", surcharge_mass_g=D(50),
                              allocation_mass_g=D(300), carton_size=4),
                     material("M-2", "50.00", index_code="INDEX-A", surcharge_mass_g=D(20),
                              allocation_mass_g=D(100), carton_size=8, stroke_mm=300)]
        authorities = Authorities(
            discount_percent=D(10), clauses={"GROUP-BOTH": "base_and_surcharge"},
            index_rates={"INDEX-A": D("0.10")}, tariffs={"TARIFF-A": D("2.00")},
            pools={"POOL-A": (D("100.00"), "largest_remainder")},
            bonus={"BONUS-A": [BonusBand(D(0), D(1000), D(1)), BonusBand(D(1000), None, D(2))]})
        shared = {"packaging_tariff": "TARIFF-A", "setup_pool": "POOL-A", "project_bonus": "BONUS-A"}
        keys = assigned({"10": {**shared, "condition_group": "GROUP-BOTH"}, "20": dict(shared)}, fees={"10": "20.00"})
        result = bid([pos("10", 10), pos("20", 20, "R-2")], materials, [keys], two_requirements(), authorities)
        first, second = self.line(result, "10"), self.line(result, "20")
        # pool: 10 x 300 g = 3000 and 20 x 100 g = 2000, so 100.00 splits 60.00 / 40.00
        # bonus: goods 10 x 100.00 = 1000.00 and 20 x 50.00 = 1000.00; 1000.00 x 1 % + 1000.00 x 2 % = 30.00,
        #        split evenly 15.00 / 15.00
        # cartons: ceil(10 / 4) = 3 and ceil(20 / 8) = 3, each 3 x 2.00 = 6.00
        # position 10 (base and surcharge discounted): 90.00 + 50 g x 0.10 x 0.9 = 4.50
        #        + (20.00 + 60.00 + 6.00 - 15.00) / 10 = 7.10
        self.assertMoney(first.unit_price, "101.60")
        # position 20 (base only): 45.00 + 20 g x 0.10 = 2.00 + (40.00 + 6.00 - 15.00) / 20 = 1.55
        self.assertMoney(second.unit_price, "48.55")
        self.assertMoney(result.total_net, "1987.00")  # 10 x 101.60 + 20 x 48.55
        self.assertEqual(result.discount_percent, D(10))
        # the reports: base before discount; surcharge = mass surcharge + setup per piece, before discount
        self.assertMoney(first.base_unit_price, "100.00")
        self.assertMoney(first.surcharge_per_unit, "13.00")  # 5.00 + (20.00 + 60.00) / 10
        self.assertMoney(first.packaging_per_unit, "0.60")  # 6.00 / 10
        self.assertMoney(first.rebate_total, "15.00")
        self.assertMoney(second.base_unit_price, "50.00")
        self.assertMoney(second.surcharge_per_unit, "4.00")  # 2.00 + 40.00 / 20
        self.assertMoney(second.packaging_per_unit, "0.30")  # 6.00 / 20
        self.assertMoney(second.rebate_total, "15.00")

    def test_the_rounded_reports_are_not_fed_back_into_the_price(self):
        keys = assigned({"10": {"packaging_tariff": "TARIFF-A"}}, fees={"10": "1.00"})
        result = bid([pos("10", 8)], [material(carton_size=10)], [keys],
                     authorities=Authorities(tariffs={"TARIFF-A": D("1.00")}))
        line = self.line(result)
        self.assertMoney(line.surcharge_per_unit, "0.13")  # 1.00 / 8 = 0.125
        self.assertMoney(line.packaging_per_unit, "0.13")  # 1 carton x 1.00 / 8 = 0.125
        self.assertMoney(line.unit_price, "10.25")  # 10.00 + 0.125 + 0.125, not 10.00 + 0.13 + 0.13
        self.assertMoney(result.total_net, "82.00")  # 8 x 10.25

    def test_the_final_price_is_rounded_half_up(self):
        result = bid([pos("10", 2)], [material()], [assigned({}, fees={"10": "0.01"})])
        self.assertMoney(self.line(result).unit_price, "10.01")  # 10.00 + 0.01 / 2 = 10.005
        self.assertMoney(result.total_net, "20.02")

    def test_the_total_adds_quantity_times_the_rounded_unit_price(self):
        materials = [material("M-1", "10.05"), material("M-2", "20.00", stroke_mm=300)]
        result = bid([pos("10", 3), pos("20", 7, "R-2")], materials, requirements=two_requirements(),
                     authorities=Authorities(discount_percent=D(10)))
        # 3 x 9.05 (9.045 rounded) = 27.15, not 3 x 9.045 = 27.135; plus 7 x 18.00 = 126.00
        self.assertMoney(result.total_net, "153.15")


class LeadTime(Case):
    """Rule 6, shared stock and delivery commitments. From stock takes 1 week, production 6 weeks."""

    def weeks(self, quantities: dict, stock: int, commitments=None, keys=None, requirements=None, sets=False) -> dict:
        materials = [material("M-1", stock=stock), material("M-2", stock=stock, stroke_mm=300)]
        answers = [assigned({number: {"delivery_commitment": key} for number, key in (keys or {}).items()})]
        positions = [pos(number, quantity, ref, sets) for number, (quantity, ref) in quantities.items()]
        result = bid(positions, materials, answers, requirements or two_requirements(),
                     Authorities(commitments=commitments or {}))
        return {line.position: line.lead_time_weeks for line in result.lines}

    def test_stock_that_covers_the_quantity_delivers_from_stock(self):
        self.assertEqual(self.weeks({"10": (50, "R-1")}, stock=50), {"10": 1})

    def test_one_piece_more_than_the_stock_means_production(self):
        self.assertEqual(self.weeks({"10": (51, "R-1")}, stock=50), {"10": 6})

    def test_positions_with_the_same_material_share_its_stock_all_or_nothing(self):
        both = {"10": (30, "R-1"), "20": (30, "R-1")}
        self.assertEqual(self.weeks(both, stock=59), {"10": 6, "20": 6})  # each fits alone, 60 together do not
        self.assertEqual(self.weeks(both, stock=60), {"10": 1, "20": 1})

    def test_positions_with_different_materials_do_not_share_stock(self):
        self.assertEqual(self.weeks({"10": (30, "R-1"), "20": (30, "R-2")}, stock=50), {"10": 1, "20": 1})

    def test_stock_is_compared_with_final_pieces(self):
        sets = {"R-1": need(pieces_per_set=6)}
        self.assertEqual(self.weeks({"10": (4, "R-1")}, 23, requirements=sets, sets=True), {"10": 6})  # 24 pieces
        self.assertEqual(self.weeks({"10": (4, "R-1")}, 24, requirements=sets, sets=True), {"10": 1})

    def test_a_commitment_applies_when_material_and_ceiling_fit(self):
        commitments = {"COMMIT-A": Commitment("M-1", 2, 60)}
        both = {"10": (30, "R-1"), "20": (30, "R-1")}
        # pooled demand 60 is within the ceiling of 60; position 20 has no commitment: 60 > 50 in stock
        self.assertEqual(self.weeks(both, 50, commitments, {"10": "COMMIT-A"}), {"10": 2, "20": 6})
        # a commitment that applies is the lead time even when the stock would cover the demand
        self.assertEqual(self.weeks(both, 60, commitments, {"10": "COMMIT-A"}), {"10": 2, "20": 1})

    def test_a_commitment_fails_when_the_pooled_demand_exceeds_its_ceiling(self):
        commitments = {"COMMIT-A": Commitment("M-1", 2, 59)}
        both = {"10": (30, "R-1"), "20": (30, "R-1")}
        # the position's own 30 would fit, the 60 for the material do not: back to shared stock
        self.assertEqual(self.weeks(both, 50, commitments, {"10": "COMMIT-A"}), {"10": 6, "20": 6})
        self.assertEqual(self.weeks(both, 60, commitments, {"10": "COMMIT-A"}), {"10": 1, "20": 1})

    def test_a_commitment_for_another_material_does_not_apply(self):
        commitments = {"COMMIT-A": Commitment("M-9", 2, 100)}
        self.assertEqual(self.weeks({"10": (30, "R-1")}, 50, commitments, {"10": "COMMIT-A"}), {"10": 1})

    def test_commitments_can_differ_between_positions_with_the_same_material(self):
        commitments = {"COMMIT-A": Commitment("M-1", 2, 100), "COMMIT-B": Commitment("M-1", 3, 100),
                       "COMMIT-C": Commitment("M-1", 4, 50)}
        three = {"10": (20, "R-1"), "20": (20, "R-1"), "30": (20, "R-1")}
        keys = {"10": "COMMIT-A", "20": "COMMIT-B", "30": "COMMIT-C"}
        # pooled demand 60: within 100 for A and B, above 50 for C, whose position falls back to production
        self.assertEqual(self.weeks(three, 50, commitments, keys), {"10": 2, "20": 3, "30": 6})


class TheAnswer(Case):
    """Bid.answer() against the answer schema of the run."""

    TOP = {"tender_reference", "decision", "currency", "discount_percent", "positions", "total_net"}
    REQUIRED = {"position", "material_number", "quantity", "unit_price", "lead_time_weeks"}
    OPTIONAL = {"base_unit_price", "surcharge_per_unit", "packaging_per_unit", "rebate_total"}

    def assertNumber(self, value, name):
        self.assertIn(type(value), (int, float), f"{name} must be a JSON number")
        self.assertGreaterEqual(value, 0, name)

    def assertSchema(self, answer: dict):
        self.assertLessEqual(self.TOP, set(answer))
        self.assertLessEqual(set(answer), self.TOP | {"notes"})
        self.assertIs(type(answer["tender_reference"]), str)
        self.assertIn(answer["decision"], ("bid", "no_bid"))
        self.assertEqual(answer["currency"], "EUR")
        self.assertNumber(answer["discount_percent"], "discount_percent")
        self.assertNumber(answer["total_net"], "total_net")
        self.assertIs(type(answer["positions"]), list)
        for entry in answer["positions"]:
            self.assertLessEqual(self.REQUIRED, set(entry))
            self.assertLessEqual(set(entry), self.REQUIRED | self.OPTIONAL)
            self.assertIs(type(entry["position"]), str)
            self.assertIs(type(entry["material_number"]), str)
            self.assertIs(type(entry["quantity"]), int)
            self.assertIs(type(entry["lead_time_weeks"]), int)
            for name in ({"unit_price"} | self.OPTIONAL) & set(entry):
                self.assertNumber(entry[name], name)
        json.dumps(answer)  # nothing in it that JSON cannot carry

    def test_a_bid_has_every_required_key_and_numbers_as_numbers(self):
        result = bid([pos()], [material()], authorities=Authorities(discount_percent=D(10)))
        answer = result.answer()
        self.assertSchema(answer)
        self.assertEqual(answer, {
            "tender_reference": "T-0001", "decision": "bid", "currency": "EUR", "discount_percent": 10,
            "positions": [{"position": "10", "material_number": "M-1", "quantity": 10, "unit_price": 9.0,
                           "lead_time_weeks": 1, "base_unit_price": 10.0, "surcharge_per_unit": 0,
                           "packaging_per_unit": 0, "rebate_total": 0}],
            "total_net": 90.0})

    def test_a_no_bid_has_no_positions_and_a_total_of_zero(self):
        answer = bid([pos()], [], no_material={"R-1"}).answer()
        self.assertSchema(answer)
        self.assertEqual(answer, {"tender_reference": "T-0001", "decision": "no_bid", "currency": "EUR",
                                  "discount_percent": 0, "positions": [], "total_net": 0})

    def test_a_fractional_discount_stays_a_number(self):
        answer = bid([pos()], [material()], authorities=Authorities(discount_percent=D("2.5"))).answer()
        self.assertSchema(answer)
        self.assertEqual(answer["discount_percent"], 2.5)

    def test_a_breakdown_field_that_is_unknown_is_left_out(self):
        answer = Bid("T-0001", "bid", D(0), [Line("10", "M-1", 5, unit_price=D("9.99"), lead_time_weeks=2)],
                     D("49.95")).answer()
        self.assertSchema(answer)
        self.assertEqual(answer["positions"], [{"position": "10", "material_number": "M-1", "quantity": 5,
                                                "unit_price": 9.99, "lead_time_weeks": 2}])
        self.assertEqual(answer["total_net"], 49.95)

    def test_a_surcharge_without_its_index_rate_is_unanswered_not_zero(self):
        metal = material(index_code="INDEX-A", surcharge_mass_g=D(250))
        answer = bid([pos()], [metal]).answer()  # no rate for INDEX-A on file
        self.assertSchema(answer)
        self.assertNotIn("surcharge_per_unit", answer["positions"][0])
        self.assertEqual(answer["positions"][0]["base_unit_price"], 10.0)

    def test_packaging_and_rebate_with_an_unresolved_key_are_unanswered_not_zero(self):
        keys = assigned({"10": {"packaging_tariff": "TARIFF-A", "project_bonus": "BONUS-A"}})
        entry = bid([pos()], [material(carton_size=10)], [keys]).answer()["positions"][0]
        self.assertNotIn("packaging_per_unit", entry)
        self.assertNotIn("rebate_total", entry)

    def test_the_full_breakdown_is_reported_in_numbers(self):
        metal = material(index_code="INDEX-A", surcharge_mass_g=D(250), carton_size=10)
        authorities = Authorities(index_rates={"INDEX-A": D("0.02")}, tariffs={"TARIFF-A": D("4.00")},
                                  bonus={"BONUS-A": [BonusBand(D(0), None, D(1))]})
        keys = assigned({"10": {"packaging_tariff": "TARIFF-A", "project_bonus": "BONUS-A"}})
        answer = bid([pos("10", 25)], [metal], [keys], authorities=authorities).answer()
        self.assertSchema(answer)
        # surcharge 250 g x 0.02 = 5.00; 3 cartons x 4.00 / 25 = 0.48; bonus 1 % of 25 x 10.00 = 2.50
        # unit price 10.00 + 5.00 + (12.00 - 2.50) / 25 = 15.38; total 25 x 15.38 = 384.50
        self.assertEqual(answer["positions"], [{
            "position": "10", "material_number": "M-1", "quantity": 25, "unit_price": 15.38, "lead_time_weeks": 1,
            "base_unit_price": 10.0, "surcharge_per_unit": 5.0, "packaging_per_unit": 0.48, "rebate_total": 2.5}])
        self.assertEqual(answer["total_net"], 384.5)


class ReadingNumbers(unittest.TestCase):
    def test_german_and_us_notation(self):
        cases = [
            ("1.234,56", None, "1234.56"), ("1,234.56", None, "1234.56"), ("1.234.567,89", None, "1234567.89"),
            ("1,234,567.89", None, "1234567.89"), ("1.234.567", None, "1234567"), ("1,234,567", None, "1234567"),
            ("12,5", None, "12.5"), ("0,85", None, "0.85"), ("12.5", None, "12.5"), ("40", None, "40"),
            ("12,345", "en-US", "12345"), ("12.345", "en-US", "12.345"),
            ("12.345", "de-DE", "12345"), ("12,345", "de-DE", "12.345"),
            ("12,345 (en-US)", None, "12345"), ("12.345 (de-DE)", None, "12345"),
            ("12,345 (en-US)", "de-DE", "12345"),  # the tag next to the number wins
            ("EUR 1.234,50", None, "1234.50"), ("1.234,50 EUR", None, "1234.50"), ("250 mm", None, "250"),
            ("2,5 %", None, "2.5"), ("-3,5", None, "-3.5"), ("1 234,56", None, "1234.56"),
            ("1 234,56", None, "1234.56"), ("1'234.56", None, "1234.56"), ("40.", None, "40"),
        ]
        for raw, number_format, expected in cases:
            with self.subTest(raw=raw, number_format=number_format):
                self.assertEqual(parse_number(raw, number_format), Decimal(expected))

    def test_a_lone_comma_is_a_decimal_comma_unless_the_format_says_otherwise(self):
        self.assertEqual(parse_number("12,345"), Decimal("12.345"))

    def test_numbers_pass_through_exactly(self):
        self.assertEqual(parse_number(12), Decimal(12))
        self.assertEqual(parse_number(0.1), Decimal("0.1"))
        self.assertEqual(parse_number(Decimal("1.10")), Decimal("1.10"))

    def test_no_number_is_none(self):
        for raw in (None, "", "   ", "n/a", True):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_number(raw))

    def test_round_cents_rounds_half_up(self):
        for raw, expected in (("0.005", "0.01"), ("0.015", "0.02"), ("0.025", "0.03"), ("2.675", "2.68"),
                              ("1.0049", "1.00"), (2.675, "2.68"), (7, "7.00")):
            with self.subTest(raw=raw):
                self.assertEqual(round_cents(raw), Decimal(expected))


class ReadingDates(unittest.TestCase):
    def test_an_iso_date_is_the_whole_day(self):
        self.assertEqual(parse_when("2030-06-15"), datetime(2030, 6, 15, tzinfo=UTC))
        self.assertEqual(parse_when("2030-06-15", end_of_day=True),
                         datetime(2030, 6, 15, 23, 59, 59, 999999, tzinfo=UTC))

    def test_an_iso_timestamp_becomes_aware_utc(self):
        for raw in ("2030-06-15T12:00:00Z", "2030-06-15T14:00:00+02:00", "2030-06-15T09:00:00-03:00",
                    "2030-06-15T12:00:00"):
            with self.subTest(raw=raw):
                when = parse_when(raw)
                self.assertEqual(when, SCENARIO)
                self.assertEqual(when.utcoffset().total_seconds(), 0)

    def test_a_timestamp_is_not_stretched_to_the_end_of_its_day(self):
        self.assertEqual(parse_when("2030-06-15T12:00:00Z", end_of_day=True), SCENARIO)

    def test_german_dates(self):
        self.assertEqual(parse_when("15.06.2030"), datetime(2030, 6, 15, tzinfo=UTC))
        self.assertEqual(parse_when("1.6.2030"), datetime(2030, 6, 1, tzinfo=UTC))
        self.assertEqual(parse_when("15.06.2030", end_of_day=True),
                         datetime(2030, 6, 15, 23, 59, 59, 999999, tzinfo=UTC))
        timed = parse_when("15.06.2030, 14:30")
        self.assertEqual((timed.year, timed.month, timed.day, timed.hour, timed.minute), (2030, 6, 15, 14, 30))
        self.assertIsNotNone(timed.tzinfo)

    def test_nothing_to_read_is_none(self):
        for raw in (None, "", "open"):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_when(raw))


class AllocatingCents(unittest.TestCase):
    def test_largest_remainder_gives_the_odd_cent_to_the_largest_fraction(self):
        # 10 cents at 1 : 2 are 3.33 and 6.67 cents: floors 3 and 6, the tenth cent goes to the .67
        self.assertEqual(allocate_cents(10, {"a": D(1), "b": D(2)}), {"a": D("0.03"), "b": D("0.07")})

    def test_largest_remainder_breaks_ties_towards_the_lower_key(self):
        # 101 cents over three equal weights: 33.67 each, floors 33, two cents left for a and b
        self.assertEqual(allocate_cents(101, {"c": D(1), "a": D(1), "b": D(1)}),
                         {"a": D("0.34"), "b": D("0.34"), "c": D("0.33")})

    def test_a_tie_is_a_tie_whatever_the_size_of_the_shares(self):
        # 5000 cents at 2000 : 500 : 500 are 3333 1/3, 833 1/3 and 833 1/3 cents: floors add up to 4999 and the
        # three remainders are equal, so the last cent goes to the lowest key
        self.assertEqual(allocate_cents(5000, {"a": D(2000), "b": D(500), "c": D(500)}),
                         {"a": D("33.34"), "b": D("8.33"), "c": D("8.33")})

    def test_remainder_to_first_and_to_last(self):
        equal = {"a": D(1), "b": D(1), "c": D(1)}  # 101 cents: floors 33, two cents left
        self.assertEqual(allocate_cents(101, equal, "remainder_to_first"),
                         {"a": D("0.35"), "b": D("0.33"), "c": D("0.33")})
        self.assertEqual(allocate_cents(101, equal, "remainder_to_last"),
                         {"a": D("0.33"), "b": D("0.33"), "c": D("0.35")})

    def test_remainder_to_largest_goes_by_weight_not_by_fraction(self):
        # 10 cents at 1 : 5 are 1.67 and 8.33 cents: floors 1 and 8; the heavier b gets the cent, not the .67
        self.assertEqual(allocate_cents(10, {"a": D(1), "b": D(5)}, "remainder_to_largest"),
                         {"a": D("0.01"), "b": D("0.09")})
        self.assertEqual(allocate_cents(10, {"a": D(1), "b": D(5)}), {"a": D("0.02"), "b": D("0.08")})

    def test_an_even_split_leaves_nothing_over(self):
        for method in ("largest_remainder", "remainder_to_first", "remainder_to_last", "remainder_to_largest"):
            with self.subTest(method=method):
                self.assertEqual(allocate_cents(10000, {"a": D(3000), "b": D(2000)}, method),
                                 {"a": D("60.00"), "b": D("40.00")})

    def test_the_shares_always_add_up_to_the_total(self):
        weights = {"a": D(7), "b": D(11), "c": D(13), "d": D("0.5")}
        for method in ("largest_remainder", "remainder_to_first", "remainder_to_last", "remainder_to_largest"):
            for cents in (1, 2, 99, 100, 12345):
                with self.subTest(method=method, cents=cents):
                    self.assertEqual(sum(allocate_cents(cents, weights, method).values()), Decimal(cents) / 100)

    def test_nothing_to_allocate_is_zero_for_everyone(self):
        self.assertEqual(allocate_cents(0, {"a": D(1), "b": D(2)}), {"a": D(0), "b": D(0)})


if __name__ == "__main__":
    unittest.main()

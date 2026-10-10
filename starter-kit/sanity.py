"""Sanity checks against model hallucinations, as switchable plugins. Plain code: no model call, no real cost.

Every check has a name, the stage where it hooks in and a status. `SANITY_CHECKS` picks which run:
    unset or "default"   every implemented check
    "all"                the same (planned checks are skipped until they exist)
    "none"               none of them
    "typing_guard,validator"   exactly these
so that the same version can be run with and without a check and the scores compared.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class Check:
    name: str
    stage: str  # where it hooks in
    catches: str
    implemented: bool


REGISTRY: dict[str, Check] = {check.name: check for check in (
    Check("validator", "before the bid is entered",
          "duplicate or foreign positions, a total that is not the sum of the lines, broken lines", True),
    Check("typing_guard", "every value the bid clerk types",
          "values that come from nowhere: an invented e-mail, a made-up price, a mistyped number", True),
    Check("no_guessed_mailbox", "bidder details handed to the clerk",
          "an unknown mailbox address filled in by guessing: the clerk asks the mailbox colleague instead", True),
    Check("grounding", "every fact the extraction returns",
          "extracted numbers, keys and identifiers that do not appear in the page they came from", False),
    Check("summary_check", "before the final signature",
          "the portal's summary disagreeing with the bid sheet (wrong dropdown, typo)", False),
)}


def enabled(name: str) -> bool:
    check = REGISTRY.get(name)
    if check is None or not check.implemented:
        return False
    choice = os.environ.get("SANITY_CHECKS", "default").strip().lower()
    if choice in ("", "default", "all"):
        return True
    if choice == "none":
        return False
    return name in {part.strip() for part in choice.split(",")}


def active() -> list[str]:
    return [name for name in REGISTRY if enabled(name)]


# ---- typing_guard -------------------------------------------------------------------------------------------------

_ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD}


def _clean(text) -> str:
    return "".join(ch for ch in str(text) if ord(ch) not in _ZERO_WIDTH).strip()


def _as_number(text: str) -> Decimal | None:
    """A typed number in German or English notation ("1.234,56", "1,234.56", "2930,65", "24"), else None."""
    raw = _clean(text).replace(" ", "").replace(" ", "")
    if not re.fullmatch(r"[+-]?[\d.,]+", raw) or not re.search(r"\d", raw):
        return None
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".") if len(raw.rsplit(",", 1)[1]) != 3 else raw.replace(",", "")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _leaves(value, out: list) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _leaves(item, out)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            _leaves(item, out)
    elif value is not None and value != "":
        out.append(value)


class TypingGuard:
    """Allows the clerk to type only what our data holds. `allow()` adds values learned during the run (a code the
    mailbox colleague read, an address it found)."""

    def __init__(self, *sources):
        self.texts: set[str] = set()
        self.numbers: set[Decimal] = set()
        for source in sources:
            self.allow(source)

    def allow(self, source) -> None:
        values: list = []
        _leaves(source, values)
        for value in values:
            text = _clean(value)
            if not text:
                continue
            self.texts.add(text.casefold())
            number = _as_number(text) if not isinstance(value, (int, float, Decimal)) else Decimal(str(value))
            if number is not None:
                self.numbers.add(number.normalize())

    def __call__(self, action: dict) -> str | None:
        """None when the action may run, else the reason it is blocked."""
        if action.get("do") != "fill":
            return None
        text = _clean(action.get("text", ""))
        if not text:
            return None  # clearing a field is always allowed
        if text.casefold() in self.texts:
            return None
        number = _as_number(text)
        if number is not None and number.normalize() in self.numbers:
            return None
        if any(text.casefold() in known or known in text.casefold() for known in self.texts if len(known) >= 6) \
                and number is None:
            return None  # the same value with a little extra around it, e.g. a code with its label
        return (f'blocked: "{text[:60]}" is not in the bid sheet, the bidder details or anything the mailbox colleague '
                "reported. Type values exactly from that data. If the form asks for something you do not have, ask "
                "the mailbox colleague (ask_mail) or leave the field empty; never make a value up.")

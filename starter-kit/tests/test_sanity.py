"""The sanity-check plugins, on invented values (no scenario values)."""

import os
import unittest
from unittest import mock

import sanity


class Switching(unittest.TestCase):
    def test_default_runs_every_implemented_check(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SANITY_CHECKS", None)
            self.assertEqual(set(sanity.active()), {c.name for c in sanity.REGISTRY.values() if c.implemented})

    def test_none_and_a_list(self):
        with mock.patch.dict(os.environ, {"SANITY_CHECKS": "none"}):
            self.assertEqual(sanity.active(), [])
        with mock.patch.dict(os.environ, {"SANITY_CHECKS": "validator, typing_guard"}):
            self.assertEqual(set(sanity.active()), {"validator", "typing_guard"})

    def test_a_planned_check_never_runs(self):
        with mock.patch.dict(os.environ, {"SANITY_CHECKS": "grounding"}):
            self.assertFalse(sanity.enabled("grounding"))


class TypingGuard(unittest.TestCase):
    def setUp(self):
        self.guard = sanity.TypingGuard({"unit_price": "1.234,56", "quantity": 12, "company": "Example Works GmbH",
                                         "email": None, "material_number": "M-100"})

    def allowed(self, text):
        return self.guard({"do": "fill", "id": 1, "text": text}) is None

    def test_values_from_the_data_pass_in_any_notation(self):
        for text in ("1.234,56", "1234,56", "1234.56", "1,234.56", "12", "Example Works GmbH", "M-100", "m-100"):
            self.assertTrue(self.allowed(text), text)

    def test_invented_values_are_blocked(self):
        for text in ("sales@example-works.example", "1234,57", "13", "Another Company"):
            self.assertFalse(self.allowed(text), text)

    def test_clearing_a_field_and_other_actions_pass(self):
        self.assertTrue(self.allowed(""))
        self.assertIsNone(self.guard({"do": "click", "id": 3}))

    def test_a_value_learned_during_the_run_is_allowed_afterwards(self):
        self.assertFalse(self.allowed("A1B2C3D4"))
        self.guard.allow("A1B2C3D4")
        self.assertTrue(self.allowed("A1B2C3D4"))

    def test_zero_width_characters_do_not_matter(self):
        self.assertTrue(self.allowed("M-" + chr(0x200B) + "100"))


if __name__ == "__main__":
    unittest.main()

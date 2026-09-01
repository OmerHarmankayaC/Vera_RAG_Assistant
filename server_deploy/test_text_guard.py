"""Tests for the repetition guard.

Stdlib only:  python -m unittest test_text_guard -v
"""

import unittest

from text_guard import (
    DEGENERATION_FALLBACK,
    DEGENERATION_NOTICE,
    RepetitionGuard,
    clean_answer,
    find_repetition_start,
)

GOOD_ANSWER = (
    "All core financial data is stored strictly on your own device. This sensitive "
    "information never leaves your phone. (source: general-terms-and-privacy.md)"
)


class DetectionTests(unittest.TestCase):
    def test_clean_text_is_left_alone(self):
        self.assertIsNone(find_repetition_start(GOOD_ANSWER))
        self.assertEqual(clean_answer(GOOD_ANSWER), GOOD_ANSWER)

    def test_repeated_word_loop_is_detected(self):
        text = "Premium sürüm, hizmetlerini " + "tamamen " * 40
        self.assertIsNotNone(find_repetition_start(text))

    def test_repeated_character_run_is_detected(self):
        self.assertIsNotNone(find_repetition_start("#" * 300))

    def test_repeated_phrase_loop_is_detected(self):
        text = "Vera Finance is not platform- " + "or platform- " * 30
        self.assertIsNotNone(find_repetition_start(text))

    def test_normal_structure_is_not_flagged(self):
        """Blank lines and bullet lists repeat, but not enough to be degeneration."""
        bullets = "Features:\n\n- Expense tracking\n- Receipt scanning\n- Savings goals\n"
        self.assertIsNone(find_repetition_start(bullets))
        self.assertIsNone(find_repetition_start("Answer.\n\n\n"))

    def test_short_repeat_is_below_the_span_threshold(self):
        self.assertIsNone(find_repetition_start("ha ha ha ha "))


class CleaningTests(unittest.TestCase):
    def test_usable_prefix_is_kept_and_annotated(self):
        text = GOOD_ANSWER + " " + "tamamen " * 40
        cleaned = clean_answer(text)

        self.assertNotIn("tamamen tamamen", cleaned)
        self.assertTrue(cleaned.endswith(DEGENERATION_NOTICE))
        self.assertIn("stored strictly on your own device", cleaned)

    def test_answer_that_is_nothing_but_noise_falls_back(self):
        self.assertEqual(clean_answer("#" * 300), DEGENERATION_FALLBACK)
        self.assertEqual(clean_answer("tamamen " * 40), DEGENERATION_FALLBACK)

    def test_cleaning_is_idempotent(self):
        cleaned = clean_answer(GOOD_ANSWER + " " + "tamamen " * 40)
        self.assertEqual(clean_answer(cleaned), cleaned)


class StreamingGuardTests(unittest.TestCase):
    def test_guard_stays_quiet_on_a_healthy_stream(self):
        guard = RepetitionGuard()
        for word in GOOD_ANSWER.split():
            self.assertFalse(guard.feed(word + " "))

    def test_guard_trips_partway_through_a_loop(self):
        guard = RepetitionGuard()
        tripped_after = None
        for i in range(60):
            if guard.feed("tamamen "):
                tripped_after = i
                break
        self.assertIsNotNone(tripped_after, "guard never detected the loop")
        # should fire within a handful of repeats, not after 60
        self.assertLess(tripped_after, 10)

    def test_guard_survives_chunks_that_split_the_repeating_unit(self):
        """Token boundaries rarely align with the repeating fragment."""
        guard = RepetitionGuard()
        stream = ("or platform- " * 30)
        tripped = any(guard.feed(stream[i : i + 3]) for i in range(0, len(stream), 3))
        self.assertTrue(tripped)


if __name__ == "__main__":
    unittest.main()

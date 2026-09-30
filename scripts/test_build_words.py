"""Tests for build_words.py. Run from the repo root:

    python3 -m unittest discover scripts
"""

import json
import tempfile
import unittest
from pathlib import Path

import build_words

MALICIOUS = ["ab`c", "${alert(1)}", "Apple", "", "café", None]


class CheckWordsTest(unittest.TestCase):
    def test_accepts_plain_lowercase_words(self):
        words = ["apace", "kneecapped"]
        self.assertIs(build_words.check_words(words, "test"), words)

    def test_rejects_anything_but_a_to_z(self):
        for word in MALICIOUS:
            with self.subTest(word=word), self.assertRaises(ValueError):
                build_words.check_words(["apace", word], "test")

    def test_error_names_the_source_and_bad_words(self):
        with self.assertRaisesRegex(ValueError, r"ENABLE: 1 invalid word\(s\): 'ab`c'"):
            build_words.check_words(["apace", "ab`c"], "ENABLE")


class SourceValidationTest(unittest.TestCase):
    """Each input and the output are checked, not just the final list."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cache = Path(tmp.name)
        (self.cache / "ted" / "days").mkdir(parents=True)
        (self.cache / "nytbee").mkdir()

        original = build_words.CACHE, build_words.OUTPUT
        self.addCleanup(lambda: setattr(build_words, "CACHE", original[0]))
        self.addCleanup(lambda: setattr(build_words, "OUTPUT", original[1]))
        build_words.CACHE = self.cache
        build_words.OUTPUT = self.cache / "words.ts"

    def write_ted_day(self, answers):
        day = {"centerLetter": "p", "validLetters": list("pkncaed"), "answers": answers}
        (self.cache / "ted" / "days" / "2025-01-01.json").write_text(json.dumps(day))

    def test_rejects_bad_enable_words(self):
        (self.cache / "enable1.txt").write_text("apace\nab`c\n")
        with self.assertRaisesRegex(ValueError, "ENABLE"):
            build_words.load_dictionary()

    def test_rejects_bad_tedmiston_answers(self):
        self.write_ted_day(["apace", "${alert(1)}"])
        with self.assertRaisesRegex(ValueError, "tedmiston 2025-01-01.json"):
            build_words.load_puzzles()

    def test_rejects_bad_nytbee_answers(self):
        (self.cache / "nytbee" / "2024-01-01.json").write_text(json.dumps(["apace", "ab`c"]))
        with self.assertRaisesRegex(ValueError, "nytbee 2024-01-01.json"):
            build_words.load_puzzles()

    def test_loads_clean_sources(self):
        self.write_ted_day(["apace", "kneecapped"])
        (self.cache / "enable1.txt").write_text("apace\n")
        self.assertEqual(len(build_words.load_puzzles()), 1)
        self.assertIn("apace", build_words.load_dictionary())

    def test_refuses_to_write_bad_output(self):
        with self.assertRaisesRegex(ValueError, "output"):
            build_words.write_words({"apace", "ab`c"})
        self.assertFalse(build_words.OUTPUT.exists())


if __name__ == "__main__":
    unittest.main()

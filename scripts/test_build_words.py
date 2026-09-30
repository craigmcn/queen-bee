"""Tests for build_words.py. Run from the repo root:

    python3 -m unittest discover scripts
"""

import contextlib
import datetime
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

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


class CacheTestCase(unittest.TestCase):
    """Points build_words at a throwaway cache and output file."""

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


class SourceValidationTest(CacheTestCase):
    """Each input and the output are checked, not just the final list."""

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



CURRENT_PAGE = """<div id="main-answer-list" class="answer-list"><ul>
<li><div class="flex-list-item">even
<a onclick="show_definition('even')">&nbsp;&#8599;&nbsp;</a></div></li>
<li><div class="flex-list-item">evening
<a onclick="show_definition('evening')">&nbsp;&#8599;&nbsp;</a></div></li>
</ul></div>"""

PRE_2020_PAGE = """<p>The official answers for today's puzzle are:</p>
<div class="answer-list"><ul class="column-list">
<li> bluff </li><li> <mark><strong>bullfrog</strong></mark> </li>
</ul></div>"""


def page(html):
    response = mock.MagicMock()
    response.read.return_value = html.encode()
    return response


class HttpErrorMixin:
    def http_error(self, code):
        error = urllib.error.HTTPError("url", code, "error", None, io.BytesIO())
        self.addCleanup(error.close)
        return error


class FetchNytbeeDayTest(HttpErrorMixin, unittest.TestCase):
    day = datetime.date(2024, 1, 1)

    def fetch(self, result):
        with mock.patch.object(build_words.urllib.request, "urlopen") as urlopen:
            urlopen.side_effect = result if isinstance(result, Exception) else None
            urlopen.return_value = None if isinstance(result, Exception) else page(result)
            return build_words.fetch_nytbee_day(self.day)

    def test_reads_current_and_pre_2020_pages(self):
        self.assertEqual(self.fetch(CURRENT_PAGE), ["even", "evening"])
        self.assertEqual(self.fetch(PRE_2020_PAGE), ["bluff", "bullfrog"])

    def test_404_means_missing(self):
        self.assertIsNone(self.fetch(self.http_error(404)))

    def test_other_http_errors_propagate(self):
        with self.assertRaises(OSError):
            self.fetch(self.http_error(503))

    def test_unreadable_page_is_a_parse_error_not_a_miss(self):
        for html in ["<p>redesigned page</p>", '<div id="main-answer-list"><ul></ul>']:
            with self.subTest(html=html), self.assertRaises(build_words.ParseError):
                self.fetch(html)


class FetchSourcesTest(HttpErrorMixin, CacheTestCase):
    """Only final results are cached, and recent parse failures stop the run."""

    today = datetime.date.today()

    def setUp(self):
        super().setUp()
        (self.cache / "enable1.txt").write_text("")
        for target, value in [
            (build_words.subprocess, "run"),
            (build_words.time, "sleep"),
        ]:
            patcher = mock.patch.object(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_fetch(self, first_age, results):
        """Fetch days from first_age days ago to today; results maps age → outcome."""

        def fetch(day):
            outcome = results.get((self.today - day).days, ["apace"])
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        output = io.StringIO()
        with (
            mock.patch.object(build_words, "FIRST_DAY", self.today - datetime.timedelta(first_age)),
            mock.patch.object(build_words, "fetch_nytbee_day", side_effect=fetch),
            contextlib.redirect_stdout(output),
        ):
            build_words.fetch_sources()
        return output.getvalue()

    def cached(self, age):
        path = self.cache / "nytbee" / f"{self.today - datetime.timedelta(age)}.json"
        return json.loads(path.read_text()) if path.exists() else "not cached"

    def test_caches_answers_and_old_404s(self):
        output = self.run_fetch(5, {4: None})
        self.assertEqual(self.cached(5), ["apace"])
        self.assertIsNone(self.cached(4))
        self.assertIn("5 fetched, 1 missing", output)

    def test_errors_and_recent_misses_are_retried(self):
        output = self.run_fetch(3, {3: self.http_error(503), 1: None, 0: build_words.ParseError("x")})
        for age in (3, 1, 0):
            self.assertEqual(self.cached(age), "not cached")
        self.assertIn("1 errors", output)
        self.assertIn("2 not posted yet", output)

    def test_recent_parse_failure_stops_the_build_uncached(self):
        with self.assertRaisesRegex(SystemExit, "markup may have changed"):
            self.run_fetch(10, {10: build_words.ParseError("no answer list found")})
        self.assertEqual(self.cached(10), "not cached")
        self.assertEqual(self.cached(9), ["apace"])

    def test_old_parse_failure_is_reported_but_not_fatal(self):
        output = self.run_fetch(40, {40: build_words.ParseError("no answer list found")})
        self.assertEqual(self.cached(40), "not cached")
        self.assertIn("1 parse failures", output)


class LoadPuzzlesTest(CacheTestCase):
    def load(self, answers):
        (self.cache / "nytbee" / "2024-01-01.json").write_text(json.dumps(answers))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            return build_words.load_puzzles(), output.getvalue()

    def test_derives_center_and_letters_from_answers(self):
        puzzles, _ = self.load(["pancaked", "kappa", "deep"])
        self.assertEqual(puzzles, [("2024-01-01", {"p"}, set("pancked"), {"pancaked", "kappa", "deep"})])

    def test_keeps_days_where_two_letters_are_in_every_answer(self):
        puzzles, _ = self.load(["pancaked", "deep", "peek"])
        self.assertEqual(puzzles[0][1], {"p", "e"})

    def test_reports_days_without_seven_letters(self):
        puzzles, output = self.load(["pace", "pane"])
        self.assertEqual(puzzles, [])
        self.assertIn("skipped 1 nytbee day(s) without 7 letters: 2024-01-01", output)


class ClassifyTest(unittest.TestCase):
    def test_ambiguous_center_only_rejects_words_with_every_required_letter(self):
        dictionary = {w: frozenset(w) for w in ["pane", "pace", "cane"]}
        puzzle = ("2024-01-01", {"p", "n"}, set("pancked"), {"pancaked"})
        verdicts = build_words.classify([puzzle], dictionary)
        self.assertEqual(verdicts["pane"], (False, "2024-01-01"))
        # Either letter could have been the center, so these get no verdict.
        self.assertNotIn("pace", verdicts)
        self.assertNotIn("cane", verdicts)


if __name__ == "__main__":
    unittest.main()

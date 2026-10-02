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


def current_item(word):
    return (
        f'<li><div class="flex-list-item">{word}\n'
        f"<a onclick=\"show_definition('{word}')\">&nbsp;&#8599;&nbsp;</a></div></li>"
    )


def answer_list(words, attrs='class="answer-list"', item=current_item):
    return f"<div {attrs}><ul>{''.join(item(w) for w in words)}</ul></div>"


# Today's layout: the official answers carry the id, and two more
# "answer-list" blocks follow with words that aren't today's answers.
CURRENT_PAGE = (
    answer_list(["pancaked", "kappa", "deep"], 'id="main-answer-list" class="answer-list"')
    + answer_list(["about", "every"])
    + answer_list(["peaked", "panda"])
)

PRE_2020_PAGE = """<p>The official answers for today's puzzle are:</p>
<div class="answer-list"><ul class="column-list">
<li> bluff </li><li> <mark><strong>bullfrog</strong></mark> </li>
</ul></div>"""

# 2019-08-17 into 2025: the id is there, but items are bare words.
MIDDLE_PAGE = """<div id="main-answer-list" class="answer-list">
<ul class="column-list">
<li>
    mono
</li>
<li>
    <mark><strong>monotony</strong></mark>
</li>
<li>
    month
</li>
<li>
    moron
</li>
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
    current = datetime.date(2024, 1, 1)
    pre_2020 = datetime.date(2019, 6, 1)

    def fetch(self, result, day=current):
        with mock.patch.object(build_words.urllib.request, "urlopen") as urlopen:
            urlopen.side_effect = result if isinstance(result, Exception) else None
            urlopen.return_value = None if isinstance(result, Exception) else page(result)
            return build_words.fetch_nytbee_day(day)

    def test_reads_each_page_layout(self):
        self.assertEqual(self.fetch(CURRENT_PAGE), ["pancaked", "kappa", "deep"])
        self.assertEqual(self.fetch(MIDDLE_PAGE), ["mono", "monotony", "month", "moron"])
        self.assertEqual(self.fetch(PRE_2020_PAGE, self.pre_2020), ["bluff", "bullfrog"])

    def test_404_means_missing(self):
        self.assertIsNone(self.fetch(self.http_error(404)))

    def test_other_http_errors_propagate(self):
        with self.assertRaises(OSError):
            self.fetch(self.http_error(503))

    def test_unreadable_page_is_a_parse_error_not_a_miss(self):
        for html in ["<p>redesigned page</p>", '<div id="main-answer-list"><ul></ul>']:
            with self.subTest(html=html), self.assertRaises(build_words.ParseError):
                self.fetch(html)

    def test_newer_page_without_the_id_doesnt_read_another_list(self):
        # If nytbee dropped the id, the first remaining list holds valid-looking
        # words that aren't the day's answers; that must fail, not get cached.
        without_id = CURRENT_PAGE.replace('id="main-answer-list" ', "")
        with self.assertRaisesRegex(build_words.ParseError, "no answer list"):
            self.fetch(without_id)

    def test_answers_that_dont_form_a_puzzle_are_a_parse_error(self):
        for words in [["about", "every"], ["pack", "need"]]:
            html = answer_list(words, 'id="main-answer-list" class="answer-list"')
            with self.subTest(words=words), self.assertRaises(build_words.ParseError):
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


    def test_latest_verdict_wins(self):
        dictionary = {"pace": frozenset("pace")}

        def puzzle(date, answers):
            return (date, {"p"}, set("pancked"), answers)

        accepted, rejected = {"pace"}, set()
        history = [
            puzzle("2019-01-01", accepted),
            puzzle("2021-01-01", rejected),
            puzzle("2023-01-01", accepted),
        ]
        self.assertEqual(build_words.classify(history, dictionary)["pace"], (True, "2023-01-01"))
        self.assertEqual(build_words.classify(history[:2], dictionary)["pace"], (False, "2021-01-01"))

    def test_words_that_never_fit_get_no_verdict(self):
        dictionary = {"zest": frozenset("zest")}
        puzzle = ("2024-01-01", {"p"}, set("pancked"), {"pancaked"})
        self.assertNotIn("zest", build_words.classify([puzzle], dictionary))


class BuildTest(unittest.TestCase):
    def test_combines_accepted_and_untested_words_minus_rejected(self):
        dictionary = {w: frozenset(w) for w in ["pace", "cane", "zoom"]}
        # "pancaked" isn't in the dictionary; "cane" fits but was left out.
        puzzle = ("2024-01-01", {"a"}, set("pancked"), {"pancaked", "pace"})
        self.assertEqual(
            build_words.build([puzzle], dictionary),
            {"pancaked", "pace", "zoom"},
        )


class DescribeChangesTest(CacheTestCase):
    def test_reads_back_written_words(self):
        self.assertEqual(build_words.read_words(), set())
        build_words.write_words({"pace", "cape"})
        self.assertEqual(build_words.read_words(), {"pace", "cape"})

    def test_summarizes_added_and_removed_words(self):
        summary = build_words.describe_changes({"pace", "abaft"}, {"pace", "pandan", "kneecap"})
        self.assertEqual(
            summary,
            "words: +2 -1 (3 total)\nadded: kneecap, pandan\nremoved: abaft",
        )

    def test_truncates_long_lists(self):
        new = {f"word{c}" for c in "abcdef"}
        summary = build_words.describe_changes(set(), new, limit=2)
        self.assertIn("added: worda, wordb, ... and 4 more", summary)
        self.assertNotIn("removed", summary)

if __name__ == "__main__":
    unittest.main()

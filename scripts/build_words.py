"""Regenerate src/data/words.ts from real NYT Spelling Bee answer history.

Usage (from the repo root; standard library only):
    python3 scripts/build_words.py [--no-fetch] [--backtest]

The list combines:
  - every word NYT accepted the last time it fit a puzzle's letters, and
  - ENABLE words that no past puzzle has tested yet,
minus words NYT left out the last time they fit. --backtest builds from all
but the most recent year of puzzles and reports how well that list predicts
the held-out year's answers.
"""

import argparse
import datetime
import http.client
import json
import re
import subprocess
import textwrap
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "scripts" / ".cache"
OUTPUT = ROOT / "src" / "data" / "words.ts"
ENABLE_URL = "https://raw.githubusercontent.com/dolph/dictionary/master/enable1.txt"
TED_REPO = "https://github.com/tedmiston/spelling-bee-answers.git"
NYTBEE_URL = "https://nytbee.com/Bee_{:%Y%m%d}.html"
# nytbee's first page with an answer list; earlier ones are 404s or empty.
FIRST_DAY = datetime.date(2018, 7, 31)
HOLDOUT_DAYS = 365
RECENT_DAYS = datetime.timedelta(days=2)
FAILURE_WINDOW = datetime.timedelta(days=30)
# nytbee added id="main-answer-list" on this day. Older pages have no id, and
# their official answers are the first "answer-list" block.
MAIN_LIST_ID_SINCE = datetime.date(2019, 8, 17)
WORD = re.compile(r"[a-z]+")


class ParseError(Exception):
    """A nytbee page loaded, but no answer list could be read from it."""


def check_words(words, source):
    """Raise if any word isn't plain a–z.

    Words are written into a JS template literal, so a backtick or "${" from
    a compromised or broken upstream would otherwise run in visitors' browsers.
    """
    bad = sorted({w for w in words if not isinstance(w, str) or not WORD.fullmatch(w)}, key=repr)
    if bad:
        shown = ", ".join(repr(w) for w in bad[:20])
        raise ValueError(f"{source}: {len(bad)} invalid word(s): {shown}")
    return words


def fetch_sources():
    CACHE.mkdir(parents=True, exist_ok=True)
    enable = CACHE / "enable1.txt"
    if not enable.exists():
        urllib.request.urlretrieve(ENABLE_URL, enable)

    ted = CACHE / "ted"
    if ted.exists():
        subprocess.run(["git", "-C", ted, "pull", "-q"], check=True)
    else:
        subprocess.run(["git", "clone", "-q", "--depth", "1", TED_REPO, ted], check=True)

    # nytbee.com fills the gaps tedmiston's archive (2023-01 to 2025-03)
    # doesn't cover. Each day is cached, and "null" marks a missing (404) page.
    # Nothing else is cached, so errors and unparsed pages are retried.
    have = {p.stem for p in (ted / "days").glob("*.json")}
    day, today = FIRST_DAY, datetime.date.today()
    counts, failed = Counter(), []
    while day <= today:
        out = CACHE / "nytbee" / f"{day.isoformat()}.json"
        if day.isoformat() not in have and not out.exists():
            status = fetch_and_cache_day(day, today, out)
            counts[status] += 1
            if status == "parse failures":
                failed.append(day)
            time.sleep(0.4)
        day += datetime.timedelta(days=1)

    print("nytbee: " + (", ".join(f"{n} {status}" for status, n in counts.items()) or "up to date"))
    # A markup change would otherwise silently stop the list learning NYT's
    # latest verdicts, so a recent parse failure stops the build.
    recent = [d for d in failed if today - d <= FAILURE_WINDOW]
    if recent:
        raise SystemExit(
            f"nytbee: couldn't parse {len(recent)} day(s) from the last "
            f"{FAILURE_WINDOW.days} days (latest {max(recent)}); the page markup may "
            "have changed, so update fetch_nytbee_day."
        )


def fetch_and_cache_day(day, today, out):
    """Fetch one nytbee day, cache it if the result is final, and return its status."""
    # A page from the last couple of days may be a placeholder or not posted
    # yet, so its miss or empty list isn't final or alarming.
    recent = today - day <= RECENT_DAYS
    try:
        answers = fetch_nytbee_day(day)
    except ParseError as error:
        if recent:
            return "not posted yet"
        print(f"{day}: {error}")
        return "parse failures"
    # IncompleteRead (a truncated response) is an HTTPException, not an
    # OSError; neither should end the run, so both are retried next time.
    except (OSError, http.client.HTTPException) as error:
        print(f"{day}: {error!r}; will retry next run")
        return "errors"
    if answers is None and recent:
        return "not posted yet"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(answers))
    return "fetched" if answers else "missing"


def fetch_nytbee_day(day):
    req = urllib.request.Request(
        NYTBEE_URL.format(day), headers={"User-Agent": "queen-bee word-list builder"}
    )
    # Only a 404 means the page doesn't exist; other errors (429, 503,
    # network) propagate so the caller retries instead of caching a miss.
    try:
        # A stray bad byte elsewhere on the page shouldn't matter; one inside
        # the answer list is caught below.
        html = urllib.request.urlopen(req, timeout=30).read().decode(errors="replace")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    # Newer pages also have "common words" and "not in today's answers"
    # lists, so if the id goes missing there, falling back to the first list
    # could quietly cache the wrong words; it's only safe for old pages.
    if day >= MAIN_LIST_ID_SINCE:
        start = html.find('id="main-answer-list"')
    else:
        start = html.find('class="answer-list"')
    if start < 0:
        raise ParseError("no answer list found")
    # Older pages list bare words and newer ones add a definition link, so
    # take the first word of each item's text rather than matching markup.
    end = html.find("</ul>", start)
    answer_list = html[start:end]
    # A replaced byte would split a word ("pan\ufffdcaked" reads as "pan"),
    # caching a fake answer and a false rejection, so treat it as unreadable.
    if "\ufffd" in answer_list:
        raise ParseError("answer list isn't valid UTF-8")
    items = re.findall(r"<li>(.*?)</li>", answer_list, re.S)
    words = [re.search(r"[a-z]+", re.sub(r"<[^>]+>", " ", item)) for item in items]
    answers = [w.group() for w in words if w]
    if not answers:
        raise ParseError("answer list is empty")
    # Real answers span exactly 7 letters (the pangram) and share the center;
    # anything else means the wrong list was read.
    letters = set().union(*answers)
    if len(letters) != 7 or not set.intersection(*(set(w) for w in answers)):
        raise ParseError(f"answers don't form a puzzle ({len(letters)} letters)")
    return answers


def load_puzzles():
    puzzles, skipped = [], []
    for path in (CACHE / "ted" / "days").glob("*.json"):
        data = json.loads(path.read_text())
        source = f"tedmiston {path.name}"
        check_words([data["centerLetter"], *data["validLetters"], *data["answers"]], source)
        puzzles.append(
            (path.stem, {data["centerLetter"]}, set(data["validLetters"]), set(data["answers"]))
        )
    for path in (CACHE / "nytbee").glob("*.json"):
        answers = json.loads(path.read_text())
        if not answers:
            continue
        check_words(answers, f"nytbee {path.name}")
        # The pangram makes the union of answer letters the full letter set.
        # The center is in every answer, but so is another letter on ~2% of
        # days; requiring all such letters only drops verdicts that depend on
        # which one was the center, so those days still count.
        required = set.intersection(*(set(w) for w in answers))
        letters = set().union(*answers)
        if len(letters) == 7:
            puzzles.append((path.stem, required, letters, set(answers)))
        else:
            skipped.append(path.stem)
    if skipped:
        print(f"skipped {len(skipped)} nytbee day(s) without 7 letters: {', '.join(sorted(skipped))}")
    return sorted(puzzles)


def load_dictionary():
    # NYT has used S in just 3 of ~2,980 puzzles, so untested S words would
    # roughly double the list for little gain; accepted S words still get in.
    words = check_words((CACHE / "enable1.txt").read_text().split(), "ENABLE")
    return {w: frozenset(w) for w in words if len(w) >= 4 and len(set(w)) <= 7 and "s" not in w}


def classify(puzzles, dictionary):
    """Each word's most recent verdict: (accepted?, date) from the last puzzle it fit.

    Latest wins because NYT prunes its list over time: many words accepted in
    2018-19 (e.g. "abaft", "canto") were left out of later puzzles they fit.
    """
    by_letters = defaultdict(set)
    for word, letters in dictionary.items():
        by_letters[letters].add(word)

    verdicts = {}
    for date, required, letters, answers in puzzles:
        for word in answers:
            by_letters[frozenset(word)].add(word)
        # A word fits when its letter set is the required letters plus any
        # subset of the rest, so ≤64 lookups replace scanning the dictionary.
        others = sorted(letters - required)
        for size in range(len(others) + 1):
            for combo in combinations(others, size):
                for word in by_letters.get(frozenset(combo) | required, ()):
                    verdicts[word] = (word in answers, date)
    return verdicts


def build(puzzles, dictionary):
    # Untested words are all kept: backtests showed filtering them by word
    # frequency lost more real answers than it saved in extras.
    verdicts = classify(puzzles, dictionary)
    accepted = {w for w, (ok, _) in verdicts.items() if ok}
    return accepted | {w for w in dictionary if w not in verdicts}


def backtest(puzzles, dictionary):
    cutoff = (datetime.date.fromisoformat(puzzles[-1][0]) - datetime.timedelta(HOLDOUT_DAYS)).isoformat()
    train = [p for p in puzzles if p[0] < cutoff]
    test = [p for p in puzzles if p[0] >= cutoff]
    words = build(train, dictionary)
    hits = extras = total = perfect = 0
    for _, required, letters, answers in test:
        found = {w for w in words if required <= set(w) <= letters}
        hits += len(found & answers)
        extras += len(found - answers)
        total += len(answers)
        perfect += not answers - found
    print(
        f"recall {hits / total:.3f}, "
        f"extras/puzzle {extras / len(test):.1f}, "
        f"puzzles fully covered {perfect}/{len(test)}"
    )


def write_words(words):
    check_words(words, "output")
    body = "\n".join(textwrap.wrap(" ".join(sorted(words)), 78))
    OUTPUT.write_text(
        "// Generated by scripts/build_words.py; rerun it to refresh.\n"
        "// Words NYT Spelling Bee accepted the last time they fit a puzzle, plus\n"
        "// ENABLE words that no past puzzle has tested yet.\n"
        "// Stored as one string rather than an array to keep the source compact.\n"
        f"const RAW = `\n{body}\n`;\n\n"
        "export const WORDS: readonly string[] = RAW.trim().split(/\\s+/);\n"
    )


def read_words():
    """The words currently in OUTPUT, or an empty set before the first build."""
    if not OUTPUT.exists():
        return set()
    match = re.search(r"`(.*)`", OUTPUT.read_text(), re.S)
    return set(match.group(1).split()) if match else set()


def describe_changes(old, new, limit=50):
    """A short added/removed summary, used in the refresh PR's description."""
    added, removed = sorted(new - old), sorted(old - new)
    lines = [f"words: +{len(added)} -{len(removed)} ({len(new)} total)"]
    for label, changed in (("added", added), ("removed", removed)):
        if changed:
            more = f", ... and {len(changed) - limit} more" if len(changed) > limit else ""
            lines.append(f"{label}: {', '.join(changed[:limit])}{more}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-fetch", action="store_true", help="use cached data only")
    parser.add_argument("--backtest", action="store_true", help="evaluate, don't write")
    args = parser.parse_args()

    if not args.no_fetch:
        fetch_sources()
    puzzles = load_puzzles()
    dictionary = load_dictionary()
    print(f"{len(puzzles)} puzzles, {puzzles[0][0]} to {puzzles[-1][0]}")

    backtest(puzzles, dictionary)
    if args.backtest:
        return

    previous = read_words()
    words = build(puzzles, dictionary)
    write_words(words)
    print(describe_changes(previous, words))


if __name__ == "__main__":
    main()

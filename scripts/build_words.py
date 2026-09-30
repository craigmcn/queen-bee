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
import json
import re
import subprocess
import textwrap
from collections import defaultdict
from itertools import combinations
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "scripts" / ".cache"
OUTPUT = ROOT / "src" / "data" / "words.ts"
ENABLE_URL = "https://raw.githubusercontent.com/dolph/dictionary/master/enable1.txt"
TED_REPO = "https://github.com/tedmiston/spelling-bee-answers.git"
NYTBEE_URL = "https://nytbee.com/Bee_{:%Y%m%d}.html"
FIRST_DAY = datetime.date(2018, 5, 9)
HOLDOUT_DAYS = 365


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
    # doesn't cover. Each day is cached, and "null" marks a missing page.
    have = {p.stem for p in (ted / "days").glob("*.json")}
    day, today = FIRST_DAY, datetime.date.today()
    while day <= today:
        out = CACHE / "nytbee" / f"{day.isoformat()}.json"
        if day.isoformat() not in have and not out.exists():
            out.parent.mkdir(exist_ok=True)
            json.dump(fetch_nytbee_day(day), out.open("w"))
            time.sleep(0.4)
        day += datetime.timedelta(days=1)


def fetch_nytbee_day(day):
    req = urllib.request.Request(
        NYTBEE_URL.format(day), headers={"User-Agent": "queen-bee word-list builder"}
    )
    try:
        html = urllib.request.urlopen(req, timeout=30).read().decode()
    except urllib.error.HTTPError:
        return None
    # Pages before 2020 have no id; their official answers are the first list.
    start = html.find('id="main-answer-list"')
    if start < 0:
        start = html.find('class="answer-list"')
    if start < 0:
        return None
    # Older pages list bare words and newer ones add a definition link, so
    # take the first word of each item's text rather than matching markup.
    end = html.find("</ul>", start)
    items = re.findall(r"<li>(.*?)</li>", html[start:end], re.S)
    words = [re.search(r"[a-z]+", re.sub(r"<[^>]+>", " ", item)) for item in items]
    return [w.group() for w in words if w] or None


def load_puzzles():
    puzzles = []
    for path in (CACHE / "ted" / "days").glob("*.json"):
        data = json.load(path.open())
        puzzles.append(
            (path.stem, data["centerLetter"], set(data["validLetters"]), set(data["answers"]))
        )
    for path in (CACHE / "nytbee").glob("*.json"):
        answers = json.load(path.open())
        if not answers:
            continue
        # The center letter is the only one in every answer; the pangram
        # guarantees the union of answer letters is the full letter set.
        common = set.intersection(*(set(w) for w in answers))
        letters = set().union(*answers)
        if len(common) == 1 and len(letters) == 7:
            puzzles.append((path.stem, common.pop(), letters, set(answers)))
    return sorted(puzzles)


def load_dictionary():
    # NYT has used S in just 2 of ~2,900 puzzles, so untested S words would
    # roughly double the list for little gain; accepted S words still get in.
    words = (CACHE / "enable1.txt").read_text().split()
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
    for date, center, letters, answers in puzzles:
        for word in answers:
            by_letters[frozenset(word)].add(word)
        # A word fits when its letter set is the center plus any subset of the
        # other six, so 64 lookups replace scanning the whole dictionary.
        others = sorted(letters - {center})
        for size in range(len(others) + 1):
            for combo in combinations(others, size):
                for word in by_letters.get(frozenset(combo) | {center}, ()):
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
    for _, center, letters, answers in test:
        found = {w for w in words if center in w and set(w) <= letters}
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
    body = "\n".join(textwrap.wrap(" ".join(sorted(words)), 78))
    OUTPUT.write_text(
        "// Generated by scripts/build_words.py; rerun it to refresh.\n"
        "// Words NYT Spelling Bee accepted the last time they fit a puzzle, plus\n"
        "// ENABLE words that no past puzzle has tested yet.\n"
        "// Stored as one string rather than an array to keep the source compact.\n"
        f"const RAW = `\n{body}\n`;\n\n"
        "export const WORDS: readonly string[] = RAW.trim().split(/\\s+/);\n"
    )


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

    words = build(puzzles, dictionary)
    write_words(words)
    print(f"wrote {len(words)} words to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

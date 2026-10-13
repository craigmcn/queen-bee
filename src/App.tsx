import { useMemo, useState } from "react";
import { LetterGridTable } from "./components/LetterGridTable";
import { PrefixList } from "./components/PrefixList";
import { WordList } from "./components/WordList";
import { useWordList } from "./data/useWordList";
import { useLetters } from "./hooks/useLetters";
import {
  buildLetterGrid,
  buildPrefixCounts,
  findWords,
  isComplete,
  isPangram,
  scoreWord,
} from "./lib/spellingBee";
import "./App.css";

function plural(count: number, noun: string) {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

function App() {
  const {
    center,
    outer,
    updateCenter,
    updateOuter,
    clear,
    centerInput,
    outerInput,
  } = useLetters();
  // Spoiler-free by default: the hints are enough to hunt with. Pangrams can
  // be revealed on their own, since they're the hardest words to find.
  const [showPangrams, setShowPangrams] = useState(false);
  const [showAllWords, setShowAllWords] = useState(false);

  const letters = center + outer;
  const complete = isComplete(letters);
  const wordList = useWordList();
  const words = useMemo(
    () =>
      wordList.status === "ready"
        ? findWords(wordList.words, center, outer)
        : [],
    [wordList, center, outer],
  );
  const pangrams = words.filter((word) => isPangram(word, letters));
  const pangramSet = new Set(pangrams);
  const points = words.reduce((total, w) => total + scoreWord(w, letters), 0);

  return (
    <main id="queen-bee" className="container">
      <h1>Queen Bee</h1>
      <p className="instructions">
        Enter the puzzle&rsquo;s center letter and its six outer letters to get
        NYT-style hints, then reveal the pangrams (words using every letter) or
        every word when you want them.
      </p>

      <form className="letters form" onSubmit={(e) => e.preventDefault()}>
        <div className="form__group">
          <label className="form__label" htmlFor="center-letter">
            Center letter
          </label>
          <input
            ref={centerInput}
            id="center-letter"
            className="form__control letters__center"
            value={center}
            onChange={(e) => updateCenter(e.target.value)}
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
          />
        </div>
        <div className="form__group">
          <label className="form__label" htmlFor="outer-letters">
            Outer letters
          </label>
          <input
            ref={outerInput}
            id="outer-letters"
            className="form__control letters__outer"
            value={outer}
            onChange={(e) => updateOuter(e.target.value)}
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
          />
        </div>
        <button type="button" className="button" onClick={clear}>
          Clear
        </button>
      </form>

      {/* Always rendered, starting empty: screen readers often skip a live
          region that's inserted with its text already in it. */}
      <p className="results-status" role="status">
        {center && wordList.status === "loading" ? "Loading words…" : ""}
      </p>

      {center && wordList.status === "error" && (
        <p className="results-status" role="alert">
          Couldn&rsquo;t load the word list. Reload the page to try again.
        </p>
      )}

      {center && wordList.status === "ready" && (
        <>
          <section className="results" aria-labelledby="results-heading">
            <h2 id="results-heading">{plural(words.length, "word")}</h2>
            {/* Pangrams need all seven letters, so a count before then would
                read as "none" rather than "not yet". */}
            <p className="stats">
              {plural(points, "point")}
              {complete && <> &middot; {plural(pangrams.length, "pangram")}</>}
            </p>
            <div className="form__check">
              <label>
                <input
                  type="checkbox"
                  checked={showPangrams}
                  onChange={(e) => setShowPangrams(e.target.checked)}
                />
                Show pangrams
              </label>
            </div>
            <div className="form__check">
              <label>
                <input
                  type="checkbox"
                  checked={showAllWords}
                  onChange={(e) => setShowAllWords(e.target.checked)}
                />
                Show all words
              </label>
            </div>
            {showPangrams && (
              <WordList
                title="Pangrams"
                words={pangrams}
                pangrams={pangramSet}
                labelPangrams={false}
                emptyMessage={
                  complete
                    ? "No pangrams."
                    : "Enter all seven letters to see pangrams."
                }
              />
            )}
            {showAllWords && (
              <WordList
                title="All words"
                words={words}
                pangrams={pangramSet}
                emptyMessage="No words."
              />
            )}
          </section>

          {words.length > 0 && (
            <>
              <section aria-labelledby="grid-heading">
                <h2 id="grid-heading">Starting letter &times; length</h2>
                <LetterGridTable grid={buildLetterGrid(words)} />
              </section>

              <section aria-labelledby="prefix-heading">
                <h2 id="prefix-heading">Two-letter list</h2>
                <PrefixList groups={buildPrefixCounts(words)} />
              </section>
            </>
          )}
        </>
      )}
    </main>
  );
}

export default App;

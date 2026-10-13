import { useMemo, useRef, useState } from "react";
import { LetterGridTable } from "./components/LetterGridTable";
import { PrefixList } from "./components/PrefixList";
import { useWordList } from "./data/useWordList";
import {
  OUTER_LETTER_COUNT,
  buildLetterGrid,
  buildPrefixCounts,
  findWords,
  isPangram,
  scoreWord,
  sanitizeLetters,
} from "./lib/spellingBee";
import "./App.css";

function App() {
  const [center, setCenter] = useState("");
  const [outer, setOuter] = useState("");
  // Spoiler-free by default: the hints are enough to hunt with. Pangrams can
  // be revealed on their own, since they're the hardest words to find.
  const [showPangrams, setShowPangrams] = useState(false);
  const [showAllWords, setShowAllWords] = useState(false);
  const outerInput = useRef<HTMLInputElement>(null);

  const letters = center + outer;
  const wordList = useWordList();
  const words = useMemo(
    () =>
      wordList.status === "ready"
        ? findWords(wordList.words, center, outer)
        : [],
    [wordList, center, outer],
  );
  const pangrams = words.filter((word) => isPangram(word, letters));
  const points = words.reduce((total, w) => total + scoreWord(w, letters), 0);

  // The center letter can't also be an outer letter, so entering it in one
  // field removes it from the other.
  const updateCenter = (value: string) => {
    const letter = sanitizeLetters(value).slice(-1);
    setCenter(letter);
    setOuter((prev) => prev.replace(letter, ""));
    // Move on once there's a letter, but not on Backspace, so the user can
    // clear and retype the center without being pulled away.
    if (letter) outerInput.current?.focus();
  };

  // Capped in state, not with maxLength: maxLength counts characters, so a
  // pasted "K, N, C, A, E, D" would be cut off before separators are stripped.
  const updateOuter = (value: string) => {
    setOuter(
      sanitizeLetters(value).replace(center, "").slice(0, OUTER_LETTER_COUNT),
    );
  };

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
        <button
          type="button"
          className="button"
          onClick={() => {
            setCenter("");
            setOuter("");
          }}
        >
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
            <h2 id="results-heading">
              {words.length} word{words.length === 1 ? "" : "s"}
            </h2>
            <p className="stats">
              {points} point{points === 1 ? "" : "s"} &middot; {pangrams.length}{" "}
              pangram{pangrams.length === 1 ? "" : "s"}
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
              <>
                <h3 id="pangrams-heading" className="word-list__heading">
                  Pangrams
                </h3>
                {/* Pangrams need all seven letters, so "none" isn't final
                    until the outer letters are complete. */}
                {outer.length < OUTER_LETTER_COUNT ? (
                  <p className="stats">
                    Enter all seven letters to see pangrams.
                  </p>
                ) : pangrams.length > 0 ? (
                  <ul className="word-list" aria-labelledby="pangrams-heading">
                    {pangrams.map((word) => (
                      <li key={word} className="word word--pangram">
                        <strong>{word}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="stats">No pangrams.</p>
                )}
              </>
            )}
            {showAllWords && (
              <>
                <h3 id="all-words-heading" className="word-list__heading">
                  All words
                </h3>
                <ul className="word-list" aria-labelledby="all-words-heading">
                  {words.map((word) =>
                    pangrams.includes(word) ? (
                      <li key={word} className="word word--pangram">
                        <strong>{word}</strong>
                        <span className="visually-hidden"> (pangram)</span>
                      </li>
                    ) : (
                      <li key={word} className="word">
                        {word}
                      </li>
                    ),
                  )}
                </ul>
              </>
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

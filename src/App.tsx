import { useMemo, useState } from "react";
import { LetterGridTable } from "./components/LetterGridTable";
import { PrefixList } from "./components/PrefixList";
import { WORDS } from "./data/words";
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
  const [hintsOnly, setHintsOnly] = useState(false);

  const letters = center + outer;
  const words = useMemo(() => findWords(WORDS, center, outer), [center, outer]);
  const pangrams = words.filter((word) => isPangram(word, letters));
  const points = words.reduce((total, w) => total + scoreWord(w, letters), 0);

  // The center letter can't also be an outer letter, so entering it in one
  // field removes it from the other.
  const updateCenter = (value: string) => {
    const letter = sanitizeLetters(value).slice(-1);
    setCenter(letter);
    setOuter((prev) => prev.replace(letter, ""));
  };

  const updateOuter = (value: string) => {
    setOuter(
      sanitizeLetters(value).replace(center, "").slice(0, OUTER_LETTER_COUNT),
    );
  };

  return (
    <main id="queen-bee" className="container">
      <h1>Queen Bee</h1>
      <p className="instructions">
        Enter the puzzle&rsquo;s center letter and its six outer letters to see
        every word of four or more letters. Pangrams (words using every letter)
        are highlighted.
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

      {center && (
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
                  checked={hintsOnly}
                  onChange={(e) => setHintsOnly(e.target.checked)}
                />
                Hints only (hide the word list)
              </label>
            </div>
            {!hintsOnly && (
              <ul className="word-list">
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

import { useId } from "react";

export function WordList({
  title,
  words,
  pangrams,
  emptyMessage,
}: {
  title: string;
  words: readonly string[];
  pangrams: ReadonlySet<string>;
  emptyMessage: string;
}) {
  const headingId = useId();
  // Among other words, the highlight needs a text equivalent; in a list of
  // only pangrams, the heading already says it.
  const labelPangrams = words.some((word) => !pangrams.has(word));

  return (
    <>
      <h3 id={headingId} className="word-list__heading">
        {title}
      </h3>
      {words.length === 0 ? (
        <p className="stats">{emptyMessage}</p>
      ) : (
        <ul className="word-list" aria-labelledby={headingId}>
          {words.map((word) =>
            pangrams.has(word) ? (
              <li key={word} className="word word--pangram">
                <strong>{word}</strong>
                {labelPangrams && (
                  <span className="visually-hidden"> (pangram)</span>
                )}
              </li>
            ) : (
              <li key={word} className="word">
                {word}
              </li>
            ),
          )}
        </ul>
      )}
    </>
  );
}

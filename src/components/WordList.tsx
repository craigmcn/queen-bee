import { useId } from "react";

export function WordList({
  title,
  words,
  pangrams,
  emptyMessage,
  labelPangrams = true,
}: {
  title: string;
  words: readonly string[];
  pangrams: ReadonlySet<string>;
  emptyMessage: string;
  labelPangrams?: boolean;
}) {
  const headingId = useId();

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
                {/* The highlight needs a text equivalent, except in the
                    Pangrams list, whose heading already says it. */}
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

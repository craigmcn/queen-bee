export const MIN_WORD_LENGTH = 4;
export const OUTER_LETTER_COUNT = 6;

/** Keeps only a–z, lowercased and de-duplicated, in first-seen order. */
export function sanitizeLetters(input: string): string {
  return [...new Set(input.toLowerCase().replace(/[^a-z]/g, ""))].join("");
}

export function findWords(
  words: readonly string[],
  center: string,
  outer: string,
): string[] {
  if (!center) return [];
  const allowed = new Set(center + outer);
  return words.filter(
    (word) =>
      word.length >= MIN_WORD_LENGTH &&
      word.includes(center) &&
      [...word].every((letter) => allowed.has(letter)),
  );
}

// NYT pangrams use all seven letters, so none count until every letter is
// entered; otherwise partial input would inflate highlights and points.
export function isPangram(word: string, letters: string): boolean {
  return (
    letters.length === OUTER_LETTER_COUNT + 1 &&
    [...letters].every((letter) => word.includes(letter))
  );
}

// NYT scoring: 4-letter words are worth 1, longer words 1 per letter, and a
// pangram earns a 7-point bonus.
export function scoreWord(word: string, letters: string): number {
  const base = word.length === MIN_WORD_LENGTH ? 1 : word.length;
  return base + (isPangram(word, letters) ? 7 : 0);
}

export interface LetterGrid {
  lengths: number[];
  rows: { letter: string; counts: number[]; total: number }[];
  columnTotals: number[];
  total: number;
}

/** Word counts by starting letter × word length, like the NYT hints grid. */
export function buildLetterGrid(words: readonly string[]): LetterGrid {
  const lengths = [...new Set(words.map((w) => w.length))].sort(
    (a, b) => a - b,
  );
  const starts = [...new Set(words.map((w) => w[0]))].sort();

  const rows = starts.map((letter) => {
    const counts = lengths.map(
      (length) =>
        words.filter((w) => w[0] === letter && w.length === length).length,
    );
    return { letter, counts, total: sum(counts) };
  });
  const columnTotals = lengths.map((_, i) =>
    sum(rows.map((row) => row.counts[i])),
  );

  return { lengths, rows, columnTotals, total: words.length };
}

/** Word counts by two-letter prefix, grouped by first letter. */
export function buildPrefixCounts(
  words: readonly string[],
): { letter: string; prefixes: { prefix: string; count: number }[] }[] {
  const counts = new Map<string, number>();
  for (const word of [...words].sort()) {
    const prefix = word.slice(0, 2);
    counts.set(prefix, (counts.get(prefix) ?? 0) + 1);
  }

  const groups = new Map<string, { prefix: string; count: number }[]>();
  for (const [prefix, count] of counts) {
    const group = groups.get(prefix[0]) ?? [];
    group.push({ prefix, count });
    groups.set(prefix[0], group);
  }
  return [...groups].map(([letter, prefixes]) => ({ letter, prefixes }));
}

function sum(values: number[]): number {
  return values.reduce((a, b) => a + b, 0);
}

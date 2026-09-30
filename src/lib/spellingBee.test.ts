import { describe, expect, it } from "vitest";
import {
  buildLetterGrid,
  buildPrefixCounts,
  findWords,
  isPangram,
  sanitizeLetters,
  scoreWord,
} from "./spellingBee";

const WORDS = [
  "acre",
  "car",
  "care",
  "caret",
  "crate",
  "react",
  "trace",
  "tract",
  "retract",
  "cater",
  "crater",
  "dance",
];

describe("sanitizeLetters", () => {
  it("lowercases, strips non-letters and removes duplicates", () => {
    expect(sanitizeLetters("A b1-aC")).toBe("abc");
  });
});

describe("findWords", () => {
  it("returns nothing without a center letter", () => {
    expect(findWords(WORDS, "", "acert")).toEqual([]);
  });

  it("requires the center letter, 4+ letters, and only allowed letters", () => {
    expect(findWords(WORDS, "t", "acre")).toEqual([
      "caret",
      "crate",
      "react",
      "trace",
      "tract",
      "retract",
      "cater",
      "crater",
    ]);
  });

  it("excludes words missing the center letter", () => {
    expect(findWords(WORDS, "c", "are")).toEqual(["acre", "care"]);
  });
});

describe("isPangram / scoreWord", () => {
  it("detects words using all seven letters", () => {
    expect(isPangram("central", "tacreln")).toBe(true);
    expect(isPangram("crater", "tacreln")).toBe(false);
  });

  it("finds no pangrams until all seven letters are entered", () => {
    expect(isPangram("crater", "acert")).toBe(false);
  });

  it("scores per NYT rules", () => {
    expect(scoreWord("care", "tacreln")).toBe(1);
    expect(scoreWord("crate", "tacreln")).toBe(5);
    expect(scoreWord("central", "tacreln")).toBe(14);
    expect(scoreWord("crate", "acert")).toBe(5);
  });
});

describe("buildLetterGrid", () => {
  it("counts words by starting letter and length with totals", () => {
    const grid = buildLetterGrid(["cart", "care", "crate", "tract", "trace"]);
    expect(grid.lengths).toEqual([4, 5]);
    expect(grid.rows).toEqual([
      { letter: "c", counts: [2, 1], total: 3 },
      { letter: "t", counts: [0, 2], total: 2 },
    ]);
    expect(grid.columnTotals).toEqual([2, 3]);
    expect(grid.total).toBe(5);
  });
});

describe("buildPrefixCounts", () => {
  it("groups two-letter prefix counts by first letter", () => {
    expect(buildPrefixCounts(["trace", "cart", "care", "crate"])).toEqual([
      {
        letter: "c",
        prefixes: [
          { prefix: "ca", count: 2 },
          { prefix: "cr", count: 1 },
        ],
      },
      { letter: "t", prefixes: [{ prefix: "tr", count: 1 }] },
    ]);
  });
});

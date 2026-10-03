import { describe, expect, it } from "vitest";
import { findWords } from "../lib/spellingBee";
import { WORDS } from "./words";

// The 2026-09-30 puzzle (center P, outer KNCAED), which the first,
// frequency-filtered list got badly wrong. Deliberately tied to live NYT
// verdicts: if a refresh PR fails here, NYT changed one of these words, so
// confirm the change and update the expectation in that PR.
describe("WORDS", () => {
  const words = findWords(WORDS, "p", "kncaed");

  it("includes NYT answers that a frequency filter missed", () => {
    for (const word of [
      "aped",
      "canape",
      "epee",
      "deadpanned",
      "kneecapped",
      "dapped",
      "neap",
      "pancaked",
      "paned",
      "pended",
    ]) {
      expect(words).toContain(word);
    }
  });

  it("excludes words NYT has rejected", () => {
    for (const word of ["kapa", "paca", "penna"]) {
      expect(words).not.toContain(word);
    }
  });
});

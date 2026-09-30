# queen-bee

NYT Spelling Bee helper: enter the center letter + six outer letters and see
every valid word (pangrams highlighted), plus the NYT-style hints grid
(starting letter × length) and two-letter prefix list. Built with React 19,
Vite 8, TypeScript 6 (strict); tooling mirrors `wordle-helper`.

## Commands

```bash
yarn dev             # dev server (http://localhost:3180)
yarn build           # tsc -b + production build → dist/
yarn build:netlify   # dual build: netlify/ (root) + netlify/queen-bee/ (GH Pages)
yarn test            # vitest watch mode
yarn test:coverage   # vitest run --coverage
yarn test:e2e        # Playwright headless E2E (run `yarn playwright install` once first)
yarn lint            # ESLint (src, e2e)
yarn format:check    # Prettier check
```

## Architecture

- **Word list:** `src/data/words.ts` — the public-domain ENABLE word-game list
  (no proper nouns, includes inflections like "tilted") filtered to 4+ letters,
  ≤7 distinct letters, and `wordfreq` Zipf frequency ≥ 2.0 (~35k words).
  NYT's list is hand-curated, so expect some extras (e.g. "etna", "nett") and
  the odd miss. The threshold favours recall: at 2.5 real answers like
  "ebbed", "yurt" and "ornery" were dropped. Stored as one whitespace-separated
  template string to keep the source compact. To regenerate, rerun the same
  filter with Python `wordfreq` over `enable1.txt`.
- **Logic:** `src/lib/spellingBee.ts` — `findWords`, `isPangram` (uses every
  entered letter), `scoreWord` (NYT scoring: 4-letter = 1, else length, +7
  pangram bonus), `buildLetterGrid`, `buildPrefixCounts`.
- **UI:** `src/App.tsx` owns the two letter inputs; entering a letter as the
  center removes it from the outer letters, and outer letters are de-duplicated
  and capped at six. Results appear once a center letter is entered.
  `LetterGridTable` shows "-" for zero cells like the NYT grid. A "Hints only"
  checkbox hides the word list (not the counts) for spoiler-free hunting.
- **Styling:** albertcss v0.18.0 via CDN link in `index.html` (container,
  `form__*`, `button`, `table--sm table--bordered`, `visually-hidden`), which
  also provides light/dark theming through `light-dark()` tokens. App CSS only
  adds layout and the Spelling Bee yellow (`src/index.css`), which keeps dark
  text in both schemes.

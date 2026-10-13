# queen-bee

An NYT Spelling Bee helper to achieve Queen Bee status.

Enter the puzzle's center letter and six outer letters to see:

- total words, points and pangrams (once all seven letters are in), and every word of four or more letters that uses the center letter (pangrams highlighted)
- a starting letter × word length grid, like the NYT Spelling Bee hints
- a two-letter list of how many words start with each two-letter prefix
- the word list hidden by default so you can hunt with just the hints; "Show pangrams" reveals only the pangrams, and "Show all words" reveals every word

## Word list

Built from ~2,980 past NYT Spelling Bee puzzles: words NYT accepted the last
time they fit a puzzle, plus untested words from the ENABLE word list. Refresh
it with `python3 scripts/build_words.py`.

## Development

```bash
yarn install
yarn dev        # http://localhost:3180
yarn test --run
yarn test:e2e
```

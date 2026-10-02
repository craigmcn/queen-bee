import { useEffect, useState } from "react";

export type WordList =
  | { status: "loading" }
  | { status: "ready"; words: readonly string[] }
  | { status: "error" };

// The word list is most of the bundle but isn't needed until a center letter
// is entered, so it loads as its own chunk instead of delaying the form.
export function useWordList(): WordList {
  const [list, setList] = useState<WordList>({ status: "loading" });

  useEffect(() => {
    let active = true;
    import("./words").then(
      ({ WORDS }) => active && setList({ status: "ready", words: WORDS }),
      () => active && setList({ status: "error" }),
    );
    return () => {
      active = false;
    };
  }, []);

  return list;
}

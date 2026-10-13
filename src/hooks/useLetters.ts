import { useRef, useState } from "react";
import { OUTER_LETTER_COUNT, sanitizeLetters } from "../lib/spellingBee";

/** The puzzle letters, kept valid as they're typed or pasted. */
export function useLetters() {
  const [center, setCenter] = useState("");
  const [outer, setOuter] = useState("");
  const centerInput = useRef<HTMLInputElement>(null);
  const outerInput = useRef<HTMLInputElement>(null);

  // The center letter can't also be an outer letter, so entering it in one
  // field removes it from the other.
  const updateCenter = (value: string) => {
    const typed = sanitizeLetters(value);
    // Take the new letter wherever the cursor was, not just the last one, so
    // typing before the current letter doesn't keep the old one.
    const letter = typed.replace(center, "").slice(-1) || typed;
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

  // Back to the start, so the next puzzle can be typed straight through.
  const clear = () => {
    setCenter("");
    setOuter("");
    centerInput.current?.focus();
  };

  return {
    center,
    outer,
    updateCenter,
    updateOuter,
    clear,
    centerInput,
    outerInput,
  };
}

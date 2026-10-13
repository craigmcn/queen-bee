import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useLetters } from "./useLetters";

describe("useLetters", () => {
  it("replaces the center with the newly typed letter", () => {
    const { result } = renderHook(() => useLetters());
    act(() => result.current.updateCenter("a"));
    // Typed before the current letter, as well as after it.
    act(() => result.current.updateCenter("ba"));
    expect(result.current.center).toBe("b");
    act(() => result.current.updateCenter("bc"));
    expect(result.current.center).toBe("c");
  });

  it("keeps the center when the same letter is typed again", () => {
    const { result } = renderHook(() => useLetters());
    act(() => result.current.updateCenter("a"));
    act(() => result.current.updateCenter("aa"));
    expect(result.current.center).toBe("a");
  });

  it("removes a new center letter from the outer letters", () => {
    const { result } = renderHook(() => useLetters());
    act(() => result.current.updateOuter("abcdef"));
    act(() => result.current.updateCenter("c"));
    expect(result.current.outer).toBe("abdef");
  });

  it("clears both fields", () => {
    const { result } = renderHook(() => useLetters());
    act(() => result.current.updateCenter("t"));
    act(() => result.current.updateOuter("acreln"));
    act(() => result.current.clear());
    expect(result.current.center).toBe("");
    expect(result.current.outer).toBe("");
  });
});

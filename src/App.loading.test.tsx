import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

type WordsModule = { WORDS: string[] };

// Mock the lazily imported word list per test; a hoisted vi.mock would be
// cached across tests even after vi.resetModules().
async function renderApp(load: () => Promise<WordsModule>) {
  vi.resetModules();
  vi.doMock("./data/words", load);
  const { default: App } = await import("./App");
  render(<App />);
}

async function enterLetters() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Center letter"), "p");
  await user.type(screen.getByLabelText("Outer letters"), "ace");
}

describe("App word-list loading", () => {
  afterEach(() => {
    vi.doUnmock("./data/words");
  });

  it("shows a loading state, then results once the list arrives", async () => {
    let resolve!: (module: WordsModule) => void;
    await renderApp(() => new Promise((r) => (resolve = r)));
    await enterLetters();

    expect(screen.getByRole("status")).toHaveTextContent("Loading words");
    expect(screen.queryByText(/0 words/)).not.toBeInTheDocument();

    resolve({ WORDS: ["pace", "cape", "peek"] });
    expect(
      await screen.findByRole("heading", { name: "2 words" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("explains when the list fails to load", async () => {
    await renderApp(() => Promise.reject(new Error("offline")));
    await enterLetters();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Couldn’t load the word list",
    );
  });

  it("shows nothing until a center letter is entered", async () => {
    await renderApp(() => new Promise(() => {}));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

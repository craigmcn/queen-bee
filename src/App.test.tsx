import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { axe } from "vitest-axe";
import App from "./App";

async function enterLetters(center: string, outer: string) {
  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText("Center letter"), center);
  await user.type(screen.getByLabelText("Outer letters"), outer);
  // The word list loads asynchronously, so wait for results to render.
  await screen.findByRole("region", { name: /words?$/ });
  return user;
}

describe("App", () => {
  it("has no detectable accessibility violations", async () => {
    const { container } = render(<App />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no accessibility violations with results shown", async () => {
    await enterLetters("t", "acreln");
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("shows no results until a center letter is entered", () => {
    render(<App />);
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("lists valid words and highlights pangrams", async () => {
    await enterLetters("t", "acreln");

    const words = within(
      screen.getByRole("region", { name: /words?$/ }),
    ).getAllByRole("listitem");
    const text = words.map((li) => li.textContent);
    expect(text).toContain("tract");
    expect(text).toContain("central (pangram)");
    expect(text.every((w) => w?.includes("t"))).toBe(true);
  });

  it("doesn't highlight pangrams until all seven letters are entered", async () => {
    await enterLetters("t", "acre");

    expect(screen.getByText(/0 pangrams/)).toBeInTheDocument();
    expect(screen.queryByText(/\(pangram\)/)).not.toBeInTheDocument();
  });

  it("moves focus to Outer letters once a center letter is typed", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText("Center letter"), "p");
    expect(screen.getByLabelText("Outer letters")).toHaveFocus();
  });

  it("keeps focus on Center letter when it's cleared", async () => {
    const user = userEvent.setup();
    render(<App />);
    const center = screen.getByLabelText("Center letter");
    await user.type(center, "p");
    await user.type(center, "{backspace}");
    expect(center).toHaveValue("");
    expect(center).toHaveFocus();
  });

  it("caps pasted outer letters at six, ignoring separators and the center", async () => {
    const user = userEvent.setup();
    render(<App />);
    // Typing the center moves focus to Outer letters, where the paste lands.
    await user.type(screen.getByLabelText("Center letter"), "p");
    await user.paste("P, K, N, C, A, E, D, X");
    expect(screen.getByLabelText("Outer letters")).toHaveValue("kncaed");
  });

  it("keeps the center letter out of the outer letters and caps them at six", async () => {
    await enterLetters("t", "tabcdefgh");
    expect(screen.getByLabelText("Outer letters")).toHaveValue("abcdef");
  });

  it("renders the letter grid and two-letter list", async () => {
    await enterLetters("t", "acreln");

    const grid = screen.getByRole("table");
    expect(
      within(grid).getByRole("rowheader", { name: "T" }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Two-letter list" })).getByText(
        /^TR-\d+$/,
      ),
    ).toBeInTheDocument();
  });

  it("hides the word list but keeps the hints in hints-only mode", async () => {
    const user = await enterLetters("t", "acreln");
    await user.click(screen.getByLabelText(/hints only/i));

    expect(screen.queryByText("tract")).not.toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Two-letter list" }),
    ).toBeInTheDocument();
  });

  it("clears the letters", async () => {
    const user = await enterLetters("t", "acreln");
    await user.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.getByLabelText("Center letter")).toHaveValue("");
    expect(screen.getByLabelText("Outer letters")).toHaveValue("");
  });
});

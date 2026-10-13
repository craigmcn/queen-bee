import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WordList } from "./WordList";

describe("WordList", () => {
  it("names the list by its heading and labels pangrams among other words", () => {
    render(
      <WordList
        title="All words"
        words={["central", "tract"]}
        pangrams={new Set(["central"])}
        emptyMessage="No words."
      />,
    );
    const items = within(
      screen.getByRole("list", { name: "All words" }),
    ).getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual([
      "central (pangram)",
      "tract",
    ]);
  });

  it("doesn't repeat the label in a list of only pangrams", () => {
    render(
      <WordList
        title="Pangrams"
        words={["central"]}
        pangrams={new Set(["central"])}
        emptyMessage="No pangrams."
      />,
    );
    expect(screen.getByRole("listitem")).toHaveTextContent(/^central$/);
  });

  it("shows the empty message instead of an empty list", () => {
    render(
      <WordList
        title="Pangrams"
        words={[]}
        pangrams={new Set()}
        emptyMessage="No pangrams."
      />,
    );
    expect(screen.getByText("No pangrams.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });
});

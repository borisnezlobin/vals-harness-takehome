import { describe, expect, it } from "vitest";

import { splitEmphasis } from "./emphasis";

describe("splitEmphasis", () => {
  it("marks text between double asterisks as strong", () => {
    expect(splitEmphasis("Meet me at **$700** today")).toEqual([
      { text: "Meet me at ", strong: false },
      { text: "$700", strong: true },
      { text: " today", strong: false },
    ]);
  });

  it("leaves unmatched asterisks alone", () => {
    expect(splitEmphasis("a ** b")).toEqual([{ text: "a ** b", strong: false }]);
  });
});

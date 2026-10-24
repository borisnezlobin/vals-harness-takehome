import { describe, expect, it } from "vitest";

import { niceStep, niceTicks } from "./ticks";

describe("ticks", () => {
  it("picks round steps", () => {
    expect(niceStep(1000, 4)).toBe(250);
    expect(niceStep(37, 4)).toBe(10);
    expect(niceStep(0, 4)).toBe(1);
  });

  it("covers the range with round values", () => {
    expect(niceTicks(130, 1520, 4)).toEqual([500, 1000, 1500]);
    expect(niceTicks(0, 100, 4)).toEqual([0, 25, 50, 75, 100]);
  });
});

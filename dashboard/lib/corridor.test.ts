import { describe, expect, it } from "vitest";

import { limitsOf, priceScale, sellerShareOfSplit, shareOfSplit, winnerOf } from "./corridor";
import type { ScenarioRecord } from "./types";

const overlap: ScenarioRecord = {
  name: "car",
  item: "a car",
  seller_minimum: 500,
  buyer_maximum: 600,
  reference_price: 550,
  reserves_overlap: true,
};

const gap: ScenarioRecord = { ...overlap, seller_minimum: 600, buyer_maximum: 500 };

describe("corridor geometry", () => {
  it("orders the limits regardless of overlap", () => {
    expect(limitsOf(overlap)).toEqual({ low: 500, high: 600 });
    expect(limitsOf(gap)).toEqual({ low: 500, high: 600 });
  });

  it("pads the scale around the limits and stretches to fit outliers", () => {
    const scale = priceScale(overlap);
    expect(scale.position(500)).toBeGreaterThan(0);
    expect(scale.position(600)).toBeLessThan(1);
    const stretched = priceScale(overlap, [2000]);
    expect(stretched.position(2000)).toBe(1);
  });

  it("never puts the scale below zero", () => {
    expect(priceScale({ ...overlap, seller_minimum: 1, buyer_maximum: 2 }).min).toBe(0);
  });

  it("measures the split from either side", () => {
    expect(sellerShareOfSplit(575, overlap)).toBeCloseTo(0.75);
    expect(shareOfSplit("buyer", 575, overlap)).toBeCloseTo(0.25);
    expect(sellerShareOfSplit(525, gap)).toBeCloseTo(0.25);
  });

  it("calls the winner", () => {
    expect(winnerOf(null, overlap)).toBeNull();
    expect(winnerOf(550, overlap)).toBe("even");
    expect(winnerOf(590, overlap)).toBe("seller");
    expect(winnerOf(510, overlap)).toBe("buyer");
  });
});

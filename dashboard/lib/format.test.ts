import { describe, expect, it } from "vitest";

import {
  formatCost,
  formatPrice,
  formatRunName,
  formatScore,
  formatShare,
  modelLabel,
  modelVendor,
  plural,
  runDate,
  scenarioLabel,
} from "./format";

describe("formatScore", () => {
  it("signs scores as percentages with a real minus sign", () => {
    expect(formatScore(0.1234)).toBe("+12.3%");
    expect(formatScore(-0.05)).toBe("−5.0%");
    expect(formatScore(-1)).toBe("−100.0%");
  });

  it("shows tiny values as zero without a sign", () => {
    expect(formatScore(0.0001)).toBe("0.0%");
    expect(formatScore(-0.0004)).toBe("0.0%");
  });

  it("shows a dash for missing values", () => {
    expect(formatScore(null)).toBe("–");
  });
});

describe("other formats", () => {
  it("formats prices, shares and costs", () => {
    expect(formatPrice(420000)).toBe("$420,000");
    expect(formatPrice(null)).toBe("–");
    expect(formatShare(0.426)).toBe("43%");
    expect(formatCost(0)).toBe("$0");
    expect(formatCost(0.0042)).toBe("$0.0042");
    expect(formatCost(1.236)).toBe("$1.24");
  });

  it("names models", () => {
    expect(modelLabel("deepseek/deepseek-v4.1-flash")).toBe("DeepSeek V4.1 Flash");
    expect(modelLabel("acme/super-model_x")).toBe("Super Model X");
    expect(modelVendor("acme/super-model")).toBe("acme");
    expect(modelVendor("local-model")).toBe("");
  });

  it("names scenarios and runs", () => {
    expect(scenarioLabel("used-car-no-overlap")).toBe("Used car no overlap");
    expect(runDate("20261023-164113")?.getHours()).toBe(16);
    expect(runDate("nope")).toBeNull();
    expect(formatRunName("nope")).toBe("nope");
    expect(formatRunName("20261023-164113")).toContain("Oct 23");
  });

  it("pluralizes", () => {
    expect(plural(1, "game")).toBe("1 game");
    expect(plural(1200, "game")).toBe("1,200 games");
  });
});

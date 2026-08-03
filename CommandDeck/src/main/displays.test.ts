import type { Display } from "electron";
import { describe, expect, it } from "vitest";

import { chooseLandscapeDisplay } from "./displays";

function display(id: number, width: number, height: number): Display {
  return {
    id,
    workArea: { x: 0, y: 0, width, height },
  } as Display;
}

describe("chooseLandscapeDisplay", () => {
  it("uses the primary display when it is landscape", () => {
    const primary = display(1, 2560, 1440);
    const portrait = display(2, 1080, 1920);

    expect(chooseLandscapeDisplay([primary, portrait], primary)).toBe(primary);
  });

  it("falls back to a landscape display when the primary is portrait", () => {
    const primary = display(1, 1080, 1920);
    const landscape = display(2, 1920, 1080);

    expect(chooseLandscapeDisplay([primary, landscape], primary)).toBe(landscape);
  });

  it("keeps the primary display when no landscape display exists", () => {
    const primary = display(1, 1080, 1920);
    const secondary = display(2, 900, 1600);

    expect(chooseLandscapeDisplay([primary, secondary], primary)).toBe(primary);
  });
});

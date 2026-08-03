import type { Display } from "electron";

/** Choose the main landscape display for apps launched by Command Deck. */
export function chooseLandscapeDisplay(
  displays: Display[],
  primary: Display,
): Display {
  if (primary.workArea.width >= primary.workArea.height) return primary;

  return (
    displays.find(
      (display) => display.workArea.width >= display.workArea.height,
    ) ?? primary
  );
}

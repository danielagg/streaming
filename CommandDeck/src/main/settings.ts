import fs from "node:fs";
import path from "node:path";
import { app, type Display } from "electron";

interface DesktopSettings {
  displayId?: string;
}

export function chooseDisplay(displays: Display[], primary: Display): Display {
  const settings = readSettings();
  const remembered = displays.find(
    (display) => String(display.id) === settings.displayId,
  );
  const secondary = displays.filter((display) => display.id !== primary.id);
  const portrait = secondary.filter(
    (display) => display.workArea.height > display.workArea.width,
  );
  return (
    portrait.find((display) => display.id === remembered?.id) ??
    portrait[0] ??
    secondary.find((display) => display.id === remembered?.id) ??
    secondary[0] ??
    remembered ??
    primary
  );
}

export function rememberDisplay(display: Display): void {
  const settingsPath = getSettingsPath();
  fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
  fs.writeFileSync(
    settingsPath,
    JSON.stringify({ displayId: String(display.id) } satisfies DesktopSettings, null, 2),
    "utf8",
  );
}

function readSettings(): DesktopSettings {
  try {
    return JSON.parse(fs.readFileSync(getSettingsPath(), "utf8")) as DesktopSettings;
  } catch {
    return {};
  }
}

function getSettingsPath(): string {
  return path.join(app.getPath("userData"), "desktop-settings.json");
}

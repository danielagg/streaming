import fs from "node:fs";
import path from "node:path";
import { app } from "electron";

import type {
  BerryActionDefinition,
  BerryActionId,
  RendererConfig,
} from "../shared/types";

interface RawConfig {
  twitch?: { channel?: string; playerParent?: string };
  actions?: Array<{
    id?: string;
    number?: string;
    name?: string;
    description?: string;
    durationMs?: number;
    accent?: string;
  }>;
}

const ACTION_IDS = new Set<BerryActionId>(["whiskey", "croak", "fly"]);

export function runtimeConfigPath(): string {
  return app.isPackaged
    ? path.join(
        process.resourcesPath,
        "resources",
        "CommandDeck",
        "config.json",
      )
    : path.join(app.getAppPath(), "config.json");
}

export function loadRendererConfig(): RendererConfig {
  const raw = JSON.parse(
    fs.readFileSync(runtimeConfigPath(), "utf8"),
  ) as RawConfig;
  const actions = (raw.actions ?? []).map((action): BerryActionDefinition => {
    if (!ACTION_IDS.has(action.id as BerryActionId)) {
      throw new Error(`Invalid Berry action id: ${action.id ?? "missing"}`);
    }
    return {
      id: action.id as BerryActionId,
      number: action.number ?? "",
      name: action.name ?? action.id!,
      description: action.description ?? "",
      durationMs: action.durationMs ?? 0,
      accent: action.accent ?? "#83e8ee",
    };
  });
  if (actions.length === 0) throw new Error("Command Deck has no Berry actions.");
  return {
    appName: "Command Deck",
    twitchChannel:
      process.env.COMMAND_DECK_TWITCH_CHANNEL ?? raw.twitch?.channel ?? "",
    twitchPlayerParent: raw.twitch?.playerParent ?? "localhost",
    actions,
  };
}

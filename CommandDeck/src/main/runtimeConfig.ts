import fs from "node:fs";
import path from "node:path";
import { app } from "electron";

import type {
  AlertEventMatcher,
  AlertEventValue,
  AlertRuleDefinition,
  AlertSeverity,
  BerryActionDefinition,
  BerryActionId,
  ObsSceneDefinition,
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
  obs?: {
    enabled?: boolean;
    scenes?: Array<{
      id?: string;
      name?: string;
      label?: string;
      accent?: string;
    }>;
    musicTailMs?: number;
    musicFadeMs?: number;
  };
}

const ACTION_IDS = new Set<BerryActionId>([
  "whiskey",
  "croak",
  "fly",
  "angry",
  "embarrassed",
  "surprised",
  "understanding",
  "vaping",
]);
const ALERT_SEVERITIES = new Set<AlertSeverity>([
  "info",
  "warning",
  "critical",
]);

function alertRulesPath(): string {
  return app.isPackaged
    ? path.join(
        process.resourcesPath,
        "resources",
        "CommandDeck",
        "alerts",
      )
    : path.join(app.getAppPath(), "alerts");
}

function isAlertEventValue(value: unknown): value is AlertEventValue {
  return ["string", "number", "boolean"].includes(typeof value);
}

function parseMatcher(value: unknown, filename: string): AlertEventMatcher {
  if (!value || typeof value !== "object") {
    throw new Error(`Invalid event matcher in alert rule ${filename}`);
  }
  const raw = value as { type?: unknown; where?: unknown };
  if (typeof raw.type !== "string" || raw.type.trim() === "") {
    throw new Error(`Alert rule ${filename} needs an event type.`);
  }
  let where: AlertEventMatcher["where"];
  if (raw.where !== undefined) {
    if (!raw.where || typeof raw.where !== "object" || Array.isArray(raw.where)) {
      throw new Error(`Alert rule ${filename} has an invalid event filter.`);
    }
    where = {};
    for (const [key, expected] of Object.entries(raw.where)) {
      const valid = Array.isArray(expected)
        ? expected.length > 0 && expected.every(isAlertEventValue)
        : isAlertEventValue(expected);
      if (!valid) {
        throw new Error(`Alert rule ${filename} has an invalid filter for ${key}.`);
      }
      where[key] = expected as AlertEventValue | AlertEventValue[];
    }
  }
  return { type: raw.type, ...(where ? { where } : {}) };
}

function parseAlertRule(value: unknown, filename: string): AlertRuleDefinition {
  if (!value || typeof value !== "object") {
    throw new Error(`Alert rule ${filename} must contain a JSON object.`);
  }
  const raw = value as {
    id?: unknown;
    message?: unknown;
    severity?: unknown;
    trigger?: { type?: unknown; durationMs?: unknown; event?: unknown };
    resolve?: { type?: unknown; event?: unknown };
  };
  if (typeof raw.id !== "string" || raw.id.trim() === "") {
    throw new Error(`Alert rule ${filename} needs an id.`);
  }
  if (typeof raw.message !== "string" || raw.message.trim() === "") {
    throw new Error(`Alert rule ${filename} needs a message.`);
  }
  if (!ALERT_SEVERITIES.has(raw.severity as AlertSeverity)) {
    throw new Error(`Alert rule ${filename} has an invalid severity.`);
  }
  if (
    raw.trigger?.type !== "inactivity" ||
    typeof raw.trigger.durationMs !== "number" ||
    !Number.isFinite(raw.trigger.durationMs) ||
    raw.trigger.durationMs <= 0
  ) {
    throw new Error(`Alert rule ${filename} has an invalid inactivity trigger.`);
  }
  if (raw.resolve?.type !== "event") {
    throw new Error(`Alert rule ${filename} has an invalid resolution.`);
  }
  return {
    id: raw.id,
    message: raw.message,
    severity: raw.severity as AlertSeverity,
    trigger: {
      type: "inactivity",
      durationMs: raw.trigger.durationMs,
      event: parseMatcher(raw.trigger.event, filename),
    },
    resolve: {
      type: "event",
      event: parseMatcher(raw.resolve.event, filename),
    },
  };
}

export function loadAlertRules(directory = alertRulesPath()): AlertRuleDefinition[] {
  if (!fs.existsSync(directory)) return [];
  const rules = fs
    .readdirSync(directory, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .sort((left, right) => left.name.localeCompare(right.name))
    .map((entry) => {
      const filename = path.join(directory, entry.name);
      return parseAlertRule(
        JSON.parse(fs.readFileSync(filename, "utf8")) as unknown,
        entry.name,
      );
    });
  const ids = new Set<string>();
  for (const rule of rules) {
    if (ids.has(rule.id)) throw new Error(`Duplicate alert rule id: ${rule.id}`);
    ids.add(rule.id);
  }
  return rules;
}

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
  const obsScenes = (raw.obs?.scenes ?? []).map((scene): ObsSceneDefinition => {
    if (!scene.id?.trim() || !scene.name?.trim()) {
      throw new Error("Every OBS scene needs an id and name.");
    }
    return {
      id: scene.id,
      name: scene.name,
      label: scene.label?.trim() || scene.name,
      accent: scene.accent ?? "#83e8ee",
    };
  });
  if (new Set(obsScenes.map((scene) => scene.id)).size !== obsScenes.length) {
    throw new Error("OBS scene ids must be unique.");
  }
  return {
    appName: "Command Deck",
    twitchChannel:
      process.env.COMMAND_DECK_TWITCH_CHANNEL ?? raw.twitch?.channel ?? "",
    twitchPlayerParent: raw.twitch?.playerParent ?? "localhost",
    actions,
    alertRules: loadAlertRules(),
    obs: {
      enabled: raw.obs?.enabled ?? false,
      scenes: obsScenes,
      musicTailMs: raw.obs?.musicTailMs ?? 30_000,
      musicFadeMs: raw.obs?.musicFadeMs ?? 5_000,
    },
  };
}

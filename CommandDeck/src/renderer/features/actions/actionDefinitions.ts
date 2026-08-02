import { Bug, GlassWater, Music2, type LucideIcon } from "lucide-react";

import type { BerryAction } from "@/types";

export type ActionDefinition = {
  action: BerryAction;
  label: string;
  icon: LucideIcon;
};

export const DEFAULT_ACTIONS: ActionDefinition[] = [
  { action: "whiskey", label: "Whiskey Sip", icon: GlassWater },
  { action: "croak", label: "Croak Twice", icon: Music2 },
  { action: "fly", label: "Fly Catch", icon: Bug },
];

export const ACTION_COLORS: Record<
  BerryAction,
  { off: string; on: string; glow: string }
> = {
  whiskey: { off: "#5d3b19", on: "#ffad32", glow: "rgba(255,169,49,.72)" },
  croak: { off: "#174b32", on: "#34db7f", glow: "rgba(52,219,127,.7)" },
  fly: { off: "#61241b", on: "#ff5b39", glow: "rgba(255,78,47,.72)" },
};

export function resolveActionDefinition(
  action: BerryAction,
  label: string,
): ActionDefinition | null {
  const fallback = DEFAULT_ACTIONS.find((item) => item.action === action);
  return fallback ? { action, label, icon: fallback.icon } : null;
}

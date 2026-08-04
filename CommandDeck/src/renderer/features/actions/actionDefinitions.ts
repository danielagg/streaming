import type { BerryAction } from "@/types";

export type ActionDefinition = {
  action: BerryAction;
  label: string;
};

export const DEFAULT_ACTIONS: ActionDefinition[] = [
  { action: "whiskey", label: "Whiskey Sip" },
  { action: "croak", label: "Croak Twice" },
  { action: "fly", label: "Fly Catch" },
  { action: "angry", label: "Angry" },
  { action: "embarrassed", label: "Embarrassed" },
  { action: "surprised", label: "Surprised" },
  { action: "understanding", label: "Understanding" },
];

export function resolveActionDefinition(
  action: BerryAction,
  label: string,
): ActionDefinition | null {
  const fallback = DEFAULT_ACTIONS.find((item) => item.action === action);
  return fallback ? { action, label } : null;
}

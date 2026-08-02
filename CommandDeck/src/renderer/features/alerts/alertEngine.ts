import type {
  AlertEventMatcher,
  AlertEventValue,
  AlertRuleDefinition,
} from "../../../shared/types";

export interface AlertEvent {
  type: string;
  payload?: Record<string, AlertEventValue>;
}

export interface AlertRuleState {
  lastSatisfiedAt: number;
  active: boolean;
}

export type AlertRuleStates = Record<string, AlertRuleState>;

export interface ActiveAlert {
  id: string;
  message: string;
  severity: AlertRuleDefinition["severity"];
  activatedAt: number;
}

export function eventMatches(
  matcher: AlertEventMatcher,
  event: AlertEvent,
): boolean {
  if (matcher.type !== event.type) return false;
  return Object.entries(matcher.where ?? {}).every(([key, expected]) => {
    const actual = event.payload?.[key];
    return Array.isArray(expected)
      ? actual !== undefined && expected.includes(actual)
      : actual === expected;
  });
}

export function initializeAlertStates(
  rules: AlertRuleDefinition[],
  now: number,
): AlertRuleStates {
  return Object.fromEntries(
    rules.map((rule) => [
      rule.id,
      { lastSatisfiedAt: now, active: false },
    ]),
  );
}

export function evaluateAlertStates(
  rules: AlertRuleDefinition[],
  states: AlertRuleStates,
  now: number,
): AlertRuleStates {
  let changed = false;
  const next = { ...states };
  for (const rule of rules) {
    const state = states[rule.id] ?? {
      lastSatisfiedAt: now,
      active: false,
    };
    const shouldBeActive =
      now - state.lastSatisfiedAt >= rule.trigger.durationMs;
    if (state.active !== shouldBeActive || !states[rule.id]) {
      next[rule.id] = { ...state, active: shouldBeActive };
      changed = true;
    }
  }
  return changed ? next : states;
}

export function applyAlertEvent(
  rules: AlertRuleDefinition[],
  states: AlertRuleStates,
  event: AlertEvent,
  now: number,
): AlertRuleStates {
  let changed = false;
  const next = { ...states };
  for (const rule of rules) {
    if (
      !eventMatches(rule.trigger.event, event) &&
      !eventMatches(rule.resolve.event, event)
    ) {
      continue;
    }
    next[rule.id] = {
      lastSatisfiedAt: now,
      active: false,
    };
    changed = true;
  }
  return changed ? next : states;
}

export function dismissAlert(
  states: AlertRuleStates,
  alertId: string,
  now: number,
): AlertRuleStates {
  const state = states[alertId];
  if (!state?.active) return states;
  return {
    ...states,
    [alertId]: { lastSatisfiedAt: now, active: false },
  };
}

export function selectActiveAlerts(
  rules: AlertRuleDefinition[],
  states: AlertRuleStates,
): ActiveAlert[] {
  return rules.flatMap((rule) => {
    const state = states[rule.id];
    return state?.active
      ? [
          {
            id: rule.id,
            message: rule.message,
            severity: rule.severity,
            activatedAt: state.lastSatisfiedAt + rule.trigger.durationMs,
          },
        ]
      : [];
  });
}

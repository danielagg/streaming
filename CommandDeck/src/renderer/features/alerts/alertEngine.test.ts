import { describe, expect, it } from "vitest";

import type { AlertRuleDefinition } from "../../../shared/types";
import {
  applyAlertEvent,
  dismissAlert,
  evaluateAlertStates,
  initializeAlertStates,
  selectActiveAlerts,
} from "./alertEngine";

const rule: AlertRuleDefinition = {
  id: "berry-animation-idle",
  message: "Long time since animation on Berry.",
  severity: "warning",
  trigger: {
    type: "inactivity",
    durationMs: 240_000,
    event: { type: "berry.action.triggered" },
  },
  resolve: {
    type: "event",
    event: { type: "berry.action.triggered" },
  },
};

describe("alert engine", () => {
  it("activates an inactivity rule at its configured duration", () => {
    const initial = initializeAlertStates([rule], 1_000);
    const early = evaluateAlertStates([rule], initial, 240_999);
    const due = evaluateAlertStates([rule], early, 241_000);

    expect(selectActiveAlerts([rule], early)).toEqual([]);
    expect(selectActiveAlerts([rule], due)).toMatchObject([
      { id: "berry-animation-idle", activatedAt: 241_000 },
    ]);
  });

  it("resolves the alert and restarts its timer on a matching event", () => {
    const active = evaluateAlertStates(
      [rule],
      initializeAlertStates([rule], 1_000),
      241_000,
    );
    const resolved = applyAlertEvent(
      [rule],
      active,
      { type: "berry.action.triggered", payload: { actionId: "croak" } },
      250_000,
    );

    expect(selectActiveAlerts([rule], resolved)).toEqual([]);
    expect(
      selectActiveAlerts(
        [rule],
        evaluateAlertStates([rule], resolved, 489_999),
      ),
    ).toEqual([]);
    expect(
      selectActiveAlerts(
        [rule],
        evaluateAlertStates([rule], resolved, 490_000),
      ),
    ).toHaveLength(1);
  });

  it("dismisses only the current occurrence and restarts its timer", () => {
    const active = evaluateAlertStates(
      [rule],
      initializeAlertStates([rule], 0),
      240_000,
    );
    const dismissed = dismissAlert(active, rule.id, 250_000);

    expect(
      selectActiveAlerts(
        [rule],
        evaluateAlertStates([rule], dismissed, 489_999),
      ),
    ).toEqual([]);
    expect(
      selectActiveAlerts(
        [rule],
        evaluateAlertStates([rule], dismissed, 490_000),
      ),
    ).toHaveLength(1);
  });
});

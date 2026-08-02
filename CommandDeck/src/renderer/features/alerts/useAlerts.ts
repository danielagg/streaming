import { useCallback, useEffect, useMemo, useState } from "react";

import type { AlertRuleDefinition } from "../../../shared/types";
import {
  applyAlertEvent,
  dismissAlert,
  evaluateAlertStates,
  initializeAlertStates,
  selectActiveAlerts,
  type AlertEvent,
} from "./alertEngine";

export function useAlerts(rules: AlertRuleDefinition[]) {
  const [states, setStates] = useState(() => initializeAlertStates(rules, Date.now()));

  useEffect(() => {
    setStates(initializeAlertStates(rules, Date.now()));
    const timer = window.setInterval(() => {
      setStates((current) => evaluateAlertStates(rules, current, Date.now()));
    }, 1_000);
    return () => window.clearInterval(timer);
  }, [rules]);

  const recordEvent = useCallback(
    (event: AlertEvent) => {
      setStates((current) => applyAlertEvent(rules, current, event, Date.now()));
    },
    [rules],
  );

  const dismiss = useCallback((alertId: string) => {
    setStates((current) => dismissAlert(current, alertId, Date.now()));
  }, []);

  const activeAlerts = useMemo(
    () => selectActiveAlerts(rules, states),
    [rules, states],
  );

  return { activeAlerts, dismiss, recordEvent };
}

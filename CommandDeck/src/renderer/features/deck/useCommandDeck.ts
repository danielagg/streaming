import { useCallback, useEffect, useRef, useState } from "react";

import { deckBridge, type RendererConfig } from "@/bridge";
import type {
  BerryAction,
  BerryActionState,
  DeckStatus,
} from "@/types";
import { useAlerts } from "@/features/alerts/useAlerts";
import type { AlertRuleDefinition } from "../../../shared/types";

const EMPTY_ACTIONS: Record<BerryAction, BerryActionState> = {
  whiskey: { action: "whiskey", phase: "idle" },
  croak: { action: "croak", phase: "idle" },
  fly: { action: "fly", phase: "idle" },
  angry: { action: "angry", phase: "idle" },
  embarrassed: { action: "embarrassed", phase: "idle" },
  surprised: { action: "surprised", phase: "idle" },
  understanding: { action: "understanding", phase: "idle" },
};

const INITIAL_STATUS: DeckStatus = {
  backend: "connecting",
  twitch: "connecting",
  remix: "connecting",
  obs: "connecting",
};

const EMPTY_ALERT_RULES: AlertRuleDefinition[] = [];
const ACTION_TIMEOUT_GRACE_MS = 7_000;

export function useCommandDeck() {
  const [config, setConfig] = useState<RendererConfig | null>(null);
  const [status, setStatus] = useState<DeckStatus>(INITIAL_STATUS);
  const [actions, setActions] = useState(EMPTY_ACTIONS);
  const [error, setError] = useState<string | null>(null);
  const actionTimeouts = useRef<Partial<Record<BerryAction, number>>>({});
  const alertRules = config?.alertRules ?? EMPTY_ALERT_RULES;
  const alerts = useAlerts(alertRules);
  const recordAlertEventRef = useRef(alerts.recordEvent);

  useEffect(() => {
    recordAlertEventRef.current = alerts.recordEvent;
  }, [alerts.recordEvent]);

  const clearActionTimeout = useCallback((action: BerryAction) => {
    const timeout = actionTimeouts.current[action];
    if (timeout !== undefined) window.clearTimeout(timeout);
    delete actionTimeouts.current[action];
  }, []);

  useEffect(() => {
    const receivedStatusEvents = new Set<keyof DeckStatus>();
    void Promise.all([deckBridge.getConfig(), deckBridge.getInitialStatus()])
      .then(([nextConfig, nextStatus]) => {
        setConfig(nextConfig);
        setStatus((current) => {
          const merged = { ...current };
          (Object.keys(nextStatus) as Array<keyof DeckStatus>).forEach((service) => {
            if (!receivedStatusEvents.has(service)) {
              merged[service] = nextStatus[service];
            }
          });
          return merged;
        });
      })
      .catch(() => setError("Could not load Command Deck configuration."));

    const unsubscribeStatus = deckBridge.subscribeStatus((update) => {
      (Object.keys(update) as Array<keyof DeckStatus>).forEach((service) =>
        receivedStatusEvents.add(service),
      );
      setStatus((current) => ({ ...current, ...update }));
    });
    const unsubscribeActions = deckBridge.subscribeActions((event) => {
      if (event.phase === "running") {
        recordAlertEventRef.current({
          type: "berry.action.triggered",
          payload: { actionId: event.action },
        });
      } else {
        clearActionTimeout(event.action);
      }
      setActions((current) => ({ ...current, [event.action]: event }));
    });
    return () => {
      unsubscribeStatus();
      unsubscribeActions();
      Object.values(actionTimeouts.current).forEach((timeout) =>
        window.clearTimeout(timeout),
      );
    };
  }, [clearActionTimeout]);

  const triggerAction = useCallback(async (action: BerryAction) => {
    setError(null);
    setActions((current) => ({
      ...current,
      [action]: { action, phase: "running", progress: 18 },
    }));
    clearActionTimeout(action);
    const durationMs =
      config?.actions.find((configured) => configured.id === action)?.durationMs ??
      0;
    actionTimeouts.current[action] = window.setTimeout(() => {
      setActions((current) =>
        current[action].phase === "running"
          ? { ...current, [action]: { action, phase: "error" } }
          : current,
      );
      setError("Berry action timed out before the backend reported completion.");
      delete actionTimeouts.current[action];
    }, durationMs + ACTION_TIMEOUT_GRACE_MS);
    try {
      await deckBridge.triggerAction(action);
    } catch (cause) {
      clearActionTimeout(action);
      setActions((current) => ({
        ...current,
        [action]: { action, phase: "error" },
      }));
      setError(cause instanceof Error ? cause.message : "Berry action failed.");
    }
  }, [clearActionTimeout, config]);

  return {
    config,
    status,
    actions,
    error,
    triggerAction,
    alerts: alerts.activeAlerts,
    dismissAlert: alerts.dismiss,
    dismissError: () => setError(null),
  };
}

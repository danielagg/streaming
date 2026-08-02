import { useCallback, useEffect, useState } from "react";

import { deckBridge, type RendererConfig } from "@/bridge";
import type {
  BerryAction,
  BerryActionState,
  DeckStatus,
} from "@/types";

const EMPTY_ACTIONS: Record<BerryAction, BerryActionState> = {
  whiskey: { action: "whiskey", phase: "idle" },
  croak: { action: "croak", phase: "idle" },
  fly: { action: "fly", phase: "idle" },
};

const INITIAL_STATUS: DeckStatus = {
  backend: "connecting",
  twitch: "connecting",
  remix: "connecting",
};

export function useCommandDeck() {
  const [config, setConfig] = useState<RendererConfig | null>(null);
  const [status, setStatus] = useState<DeckStatus>(INITIAL_STATUS);
  const [actions, setActions] = useState(EMPTY_ACTIONS);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([deckBridge.getConfig(), deckBridge.getInitialStatus()])
      .then(([nextConfig, nextStatus]) => {
        setConfig(nextConfig);
        setStatus(nextStatus);
      })
      .catch(() => setError("Could not load Command Deck configuration."));

    const unsubscribeStatus = deckBridge.subscribeStatus((update) =>
      setStatus((current) => ({ ...current, ...update })),
    );
    const unsubscribeActions = deckBridge.subscribeActions((event) =>
      setActions((current) => ({ ...current, [event.action]: event })),
    );
    return () => {
      unsubscribeStatus();
      unsubscribeActions();
    };
  }, []);

  const triggerAction = useCallback(async (action: BerryAction) => {
    setError(null);
    setActions((current) => ({
      ...current,
      [action]: { action, phase: "running", progress: 18 },
    }));
    try {
      await deckBridge.triggerAction(action);
    } catch (cause) {
      setActions((current) => ({
        ...current,
        [action]: { action, phase: "error" },
      }));
      setError(cause instanceof Error ? cause.message : "Berry action failed.");
    }
  }, []);

  return {
    config,
    status,
    actions,
    error,
    triggerAction,
    dismissError: () => setError(null),
  };
}

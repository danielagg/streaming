import type { BackendEvent } from "./types";

const BACKEND_EVENT_TYPES = new Set<BackendEvent["type"]>([
  "service.status",
  "remix.preview.ready",
  "chat.message",
  "berry.action.progress",
  "berry.action.completed",
  "berry.action.error",
]);

export function isBackendEvent(value: unknown): value is BackendEvent {
  if (!value || typeof value !== "object") return false;
  const candidate = value as { type?: unknown; payload?: unknown };
  return (
    typeof candidate.type === "string" &&
    BACKEND_EVENT_TYPES.has(candidate.type as BackendEvent["type"]) &&
    !!candidate.payload &&
    typeof candidate.payload === "object"
  );
}

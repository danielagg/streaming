import { describe, expect, it } from "vitest";

import { isBackendEvent } from "./protocol";

describe("isBackendEvent", () => {
  it("accepts a versioned service status event", () => {
    expect(
      isBackendEvent({
        version: 1,
        type: "service.status",
        payload: { service: "remix", state: "online" },
      }),
    ).toBe(true);
    expect(
      isBackendEvent({
        version: 1,
        type: "obs.scene.changed",
        payload: { sceneName: "Starting Soon" },
      }),
    ).toBe(true);
    expect(
      isBackendEvent({
        version: 1,
        type: "backend.ready",
        payload: { name: "Command Deck", protocolVersion: 1, actions: [] },
      }),
    ).toBe(true);
    expect(
      isBackendEvent({
        version: 1,
        type: "command.result",
        requestId: "request-1",
        payload: { ok: true, accepted: true },
      }),
    ).toBe(true);
    expect(
      isBackendEvent({
        version: 1,
        type: "remix.preview.ready",
        payload: {},
      }),
    ).toBe(true);
  });

  it("rejects unknown event types and missing payloads", () => {
    expect(isBackendEvent({ type: "something.unknown", payload: {} })).toBe(false);
    expect(isBackendEvent({ type: "chat.message" })).toBe(false);
  });
});

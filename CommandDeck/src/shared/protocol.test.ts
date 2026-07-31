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
        type: "remix.preview.ready",
        payload: {},
      }),
    ).toBe(true);
  });

  it("rejects unknown event types and missing payloads", () => {
    expect(isBackendEvent({ type: "backend.ready", payload: {} })).toBe(false);
    expect(isBackendEvent({ type: "chat.message" })).toBe(false);
  });
});

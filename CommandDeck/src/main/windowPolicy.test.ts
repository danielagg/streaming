import { describe, expect, it } from "vitest";

import { isExternalHttpsUrl, isTwitchOwnedUrl } from "./windowPolicy";

describe("Twitch popup policy", () => {
  it.each([
    "https://www.twitch.tv/login",
    "https://passport.twitch.tv/login",
    "https://id.twitch.tv/oauth2/authorize",
    "https://twitch.tv/",
  ])("keeps Twitch-owned pages in the app session: %s", (url) => {
    expect(isTwitchOwnedUrl(url)).toBe(true);
  });

  it.each([
    "http://www.twitch.tv/login",
    "https://twitch.tv.example.com/login",
    "https://eviltwitch.tv/login",
    "https://example.com/?next=https://twitch.tv",
    "not a url",
  ])("rejects untrusted lookalikes: %s", (url) => {
    expect(isTwitchOwnedUrl(url)).toBe(false);
  });

  it("only classifies valid HTTPS links as externally openable", () => {
    expect(isExternalHttpsUrl("https://example.com/path")).toBe(true);
    expect(isExternalHttpsUrl("http://example.com/path")).toBe(false);
    expect(isExternalHttpsUrl("javascript:alert(1)")).toBe(false);
    expect(isExternalHttpsUrl("not a url")).toBe(false);
  });
});

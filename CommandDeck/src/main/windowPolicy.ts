export function isTwitchOwnedUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:" &&
      (url.hostname === "twitch.tv" || url.hostname.endsWith(".twitch.tv"))
    );
  } catch {
    return false;
  }
}

export function isExternalHttpsUrl(value: string): boolean {
  try {
    return new URL(value).protocol === "https:";
  } catch {
    return false;
  }
}

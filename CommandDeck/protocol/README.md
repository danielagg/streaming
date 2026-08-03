# Command Deck protocol

Electron owns the desktop window and the Python sidecar owns integrations. They
communicate over a WebSocket bound to `127.0.0.1` only.

Every command includes protocol `version: 1`, a unique `id`, a `type`, and a
payload. Every response that completes a command uses `command.result` and
copies the command ID into `requestId`. Unsolicited backend events omit
`requestId`.

The Electron process generates a random session token each time it launches the
sidecar, passes it in `COMMAND_DECK_TOKEN`, and supplies it as the WebSocket
`token` query parameter. The backend must reject missing or incorrect tokens.

## Examples

```json
{
  "version": 1,
  "id": "01K1...",
  "type": "action.trigger",
  "payload": { "actionId": "croak" }
}
```

```json
{
  "version": 1,
  "type": "berry.action.progress",
  "payload": { "actionId": "croak", "remainingMs": 1750 }
}
```

```json
{
  "version": 1,
  "id": "01K2...",
  "type": "obs.scene.set",
  "payload": { "sceneName": "Starting Soon" }
}
```

```json
{
  "version": 1,
  "type": "obs.music.tail",
  "payload": { "state": "fading", "remainingMs": 4200 }
}
```

```json
{
  "version": 1,
  "type": "chat.message",
  "payload": {
    "id": "message-id",
    "author": "viewer",
    "message": "Hello Berry!",
    "timestamp": "2026-07-31T18:00:00Z"
  }
}
```

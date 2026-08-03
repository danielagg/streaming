# Command Deck

Command Deck is a portrait-first Windows control surface for the stream. It is
designed to run fullscreen on a rotated monitor and currently contains:

- a 16:9 Twitch stream monitor;
- Twitch's live embedded chat surface;
- compact Whiskey Sip, Croak Twice, and Fly Catch controls for Berry;
- a manually managed, reorderable sound-effects panel;
- live OBS scene controls with Starting Soon music-tail automation;
- automatic PNGTuber Remix launch, state control, state restoration, and Croak
  audio playback.

The visible application is React and TypeScript inside a secure Electron shell.
A bundled Python sidecar owns TwitchIO, PNGTuber Remix, and audio. Electron and
Python communicate over an authenticated WebSocket bound
only to `127.0.0.1`.

## Current state

The desktop UI, Twitch player and live chat, Berry controls, backend protocol,
Windows packaging, and GitHub Actions pipeline are implemented. The chat panel
uses Twitch's supported embed so live messages work without storing Twitch
credentials in Command Deck.

The OBS panel controls the configured live scenes through OBS WebSocket v5 and
tracks scene changes made in either OBS or Command Deck. Moving from `Starting
Soon` to `Main (screen share)` keeps the shared `StartingSoon Music` media source
playing, then fades it over the final five seconds and stops it 30 seconds after
the scene change.

## Configure

Edit `config.json` before starting a development build. At minimum, set
`twitch.channel` to the Twitch channel name to enable the stream monitor.

Do not commit Twitch tokens or client secrets. The Twitch chat embed does not
need either one.

Enable the OBS WebSocket server under **OBS > Tools > WebSocket Server
Settings**. Command Deck connects to `ws://127.0.0.1:4455`. Keep OBS
authentication enabled and place only the password in an ignored local file at
`obs-password.txt` beside this README, or set `COMMAND_DECK_OBS_PASSWORD` before
launching Command Deck. The local password file is never packaged or committed.

OBS scene names, the music input name, and the tail/fade durations are configured
in the `obs` section of `config.json`. `StartingSoon Music` must be the same OBS
Media Source reference in both `Starting Soon` and `Main (screen share)`.

Sound effects are discovered from `../Audio/Manual` during local development.
Add or remove MP3 files there while Command Deck is open and the panel updates
automatically. Reordering in the panel is saved under Electron's per-user app
data and is restored on the next launch; newly discovered files are appended.
Packaged builds use `Audio/Manual` beside the executable. Set
`COMMAND_DECK_MANUAL_AUDIO_DIR` to use a different directory.

Alert rules live as individual JSON files in `alerts/`. The renderer's alert
engine evaluates these rules against named application events, so panels and
buttons do not contain rule-specific trigger or resolution logic. For example,
`berry-animation-idle.json` watches for four minutes without a
`berry.action.triggered` event and uses that same event to resolve the alert.

Each alert file has this shape:

```json
{
  "id": "unique-alert-id",
  "message": "Message shown in the alert panel.",
  "severity": "warning",
  "trigger": {
    "type": "inactivity",
    "durationMs": 240000,
    "event": { "type": "application.event.name" }
  },
  "resolve": {
    "type": "event",
    "event": { "type": "application.event.name" }
  }
}
```

An event matcher can optionally contain a `where` object to match payload
properties. A property may be one value or an array of accepted values.

The Remix executable path currently points to:

```text
C:/Users/Daniel/Downloads/PNGTuber-Remix-win32-x86_64/PNGTuber-Remix.exe
```

Update `remix.executablePath` if Remix moves.

## Develop

For the normal local workflow, double-click `Start Command Deck.cmd`. It installs
missing dependencies, builds the current source, and launches Command Deck.
The app starts maximized on the selected portrait monitor as a normal Windows
window with minimize, maximize, and close buttons.

For manual development, requirements are Node.js and Python 3.12 or newer:

```powershell
npm.cmd ci
python -m pip install -e "backend[dev,twitch]" pyinstaller
npm.cmd run dev
```

Set `COMMAND_DECK_START_MAXIMIZED=0` before launching to start at its normal
window size instead of maximized.

## Verify

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
python -m pytest backend/tests
python -m ruff check backend
npm.cmd run make
```

`npm.cmd run make` builds the React application, freezes the Python sidecar,
stages the Berry model/audio, and creates both a Windows installer and a portable
ZIP under `out/make`.

## CI/CD

`.github/workflows/command-deck.yml` runs the TypeScript and Python checks in
parallel. Windows packaging only runs after both jobs pass. Main-branch builds
are uploaded as workflow artifacts, and tags matching `command-deck-v*` create a
GitHub Release.

The former Tkinter implementation is retained unchanged in `_old` as a backup
and behavioral reference.

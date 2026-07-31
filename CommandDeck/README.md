# Command Deck

Command Deck is a portrait-first Windows control surface for the stream. It is
designed to run fullscreen on a rotated monitor and currently contains:

- a 16:9 Twitch stream monitor;
- a native real-time chat surface;
- stacked Whiskey Sip, Croak Twice, and Fly Catch controls for Berry;
- F13, F14, and F15 triple-press global hotkeys;
- automatic PNGTuber Remix launch, state control, state restoration, and Croak
  audio playback.

The visible application is React and TypeScript inside a secure Electron shell.
A bundled Python sidecar owns TwitchIO, PNGTuber Remix, audio, and Windows
hotkeys. Electron and Python communicate over an authenticated WebSocket bound
only to `127.0.0.1`.

## Current state

The desktop UI, Twitch player, Berry controls, backend protocol, Windows
packaging, and GitHub Actions pipeline are implemented. TwitchIO is packaged and
its lifecycle boundary is in place; authorization and the live EventSub chat
subscription are the next feature slice. Until that is connected, the packaged
chat panel remains in its waiting state. Running the renderer without Electron
uses demonstration chat data for interface development.

## Configure

Edit `config.json` before starting a development build. At minimum, set
`twitch.channel` to the Twitch channel name to enable the stream monitor.

Do not commit Twitch tokens or client secrets. The empty Twitch authorization
fields are placeholders for the upcoming device-code login flow.

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

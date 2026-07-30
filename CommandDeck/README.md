# Command Deck

Command Deck is a Windows control surface for stream actions. The first control
group, **Berry Animations**, provides three large on-screen controls plus
temporary global hotkeys:

- **Whiskey Sip** — enters `Whiskey Sip` for 2 seconds
- **Croak Twice** — enters `Croaking`, plays the synchronized MP3, and returns
  after 3 seconds
- **Fly Catch** — enters `Fly Catch` for 1.4 seconds

Each action remembers the active normal PNGTuber Remix state and restores it
when the animation finishes. Command Deck does not launch PowerShell.

The temporary global controls require three quick presses within 1.2 seconds:

- `F13` ×3 — Whiskey Sip
- `F14` ×3 — Croak Twice
- `F15` ×3 — Fly Catch

They work while another Windows app has focus. Set
`global_hotkeys.enabled` to `false` in `config.json` to disable them.

## Start it

1. Open **Command Deck** from the Windows Start menu, or double-click
   `CommandDeck.exe` / `Start Command Deck.cmd`.
2. Command Deck automatically opens `Berry/Berry.pngRemix`, waits up to 30
   seconds for Remix, forces **Preview** mode with a **transparent**
   background, and changes its top-right status to `ONLINE`.
3. Click an action card, or quickly press its assigned hotkey three times.

If Remix was not ready when Command Deck opened, click the red `OFFLINE` status
in the top-right corner to retry. Its local WebSocket server must be configured
to start automatically on port `9321`.

Set `auto_launch_remix` to `false` in `config.json` if you ever want to disable
the automatic model launch.

The startup guarantees can be controlled independently with
`force_remix_preview` and `force_transparent_background` in `config.json`.
Preview selection is sent directly to the Remix window after its WebSocket
server reports ready; it does not move the mouse or require keyboard shortcuts.
When that setup is complete, Windows focus is returned to Command Deck.

Command Deck currently launches:

`C:/Users/Daniel/Downloads/PNGTuber-Remix-win32-x86_64/PNGTuber-Remix.exe`

If Remix is moved or updated into another folder, change
`remix_executable_path` in `config.json`.

## Required Remix state names

The Remix model must contain these exact state names:

- `Whiskey Sip`
- `Croaking`
- `Fly Catch`

The old PowerShell helpers do not need to be open. Leaving them closed avoids
duplicate triggers and competing WebSocket connections.

## Configuration

Edit `config.json` to change the WebSocket address, action duration, state name,
label, description, accent color, audio path, global-hotkey mappings and timing,
or Remix executable. Relative paths are resolved from the `CommandDeck` folder.

The application uses only Python's standard library:

- Tkinter for the desktop GUI
- a local RFC 6455 WebSocket client for Remix
- the Windows Media Control Interface for MP3 playback
- native Windows global-hotkey registration through `ctypes`

That deliberately small foundation leaves room for later modules such as
TwitchIO without making the dashboard dependent on a browser or Electron.

## Windows build

`CommandDeck.exe` is a windowed one-file build with Berry embedded as its
multi-resolution Windows icon. Run `py -3.13 build_windows.py` after source
changes to rebuild it. Pillow and PyInstaller are build-time dependencies only.

# Command Deck

Command Deck is a click-only Windows control surface for stream actions. The
first control group, **Berry Animations**, replaces the old F13/F14/F15 helper
workflow with three large on-screen controls:

- **Whiskey Sip** — enters `Whiskey Sip` for 2 seconds
- **Croak Twice** — enters `Croaking`, plays the synchronized MP3, and returns
  after 3 seconds
- **Fly Catch** — enters `Fly Catch` for 1.4 seconds

Each action remembers the active normal PNGTuber Remix state and restores it
when the animation finishes. Command Deck does not register keyboard shortcuts
and does not launch PowerShell.

## Start it

1. Double-click `Start Command Deck.cmd`.
2. Command Deck automatically opens `Berry/Berry.pngRemix`, waits up to 30
   seconds for Remix, and changes its top-right status to `ONLINE`.
3. Click an action card.

If Remix was not ready when Command Deck opened, click the red `OFFLINE` status
in the top-right corner to retry. Its local WebSocket server must be configured
to start automatically on port `9321`.

Set `auto_launch_remix` to `false` in `config.json` if you ever want to disable
the automatic model launch.

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
label, description, accent color, audio path, or Remix executable. Relative
paths are resolved from the `CommandDeck` folder.

The application uses only Python's standard library:

- Tkinter for the desktop GUI
- a local RFC 6455 WebSocket client for Remix
- the Windows Media Control Interface for MP3 playback

That deliberately small foundation leaves room for later modules such as
TwitchIO without making the dashboard dependent on a browser or Electron.

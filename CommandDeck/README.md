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

1. Start PNGTuber Remix.
2. In Remix, start the local WebSocket server on port `9321`.
3. Double-click `Start Command Deck.cmd`.
4. Wait for the top-right status to read `ONLINE`.
5. Click an action card.

If Remix was not ready when Command Deck opened, click the red `OFFLINE` status
in the top-right corner to retry.

## Required Remix state names

The Remix model must contain these exact state names:

- `Whiskey Sip`
- `Croaking`
- `Fly Catch`

The old PowerShell helpers do not need to be open. Leaving them closed avoids
duplicate triggers and competing WebSocket connections.

## Configuration

Edit `config.json` to change the WebSocket address, action duration, state name,
label, description, accent color, or audio path. Paths are resolved relative to
the `CommandDeck` folder.

The application uses only Python's standard library:

- Tkinter for the desktop GUI
- a local RFC 6455 WebSocket client for Remix
- the Windows Media Control Interface for MP3 playback

That deliberately small foundation leaves room for later modules such as
TwitchIO without making the dashboard dependent on a browser or Electron.

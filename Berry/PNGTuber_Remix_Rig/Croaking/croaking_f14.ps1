param(
    [string]$CroakState = "Croaking",
    [int]$DurationMs = 3000,
    [string]$WebSocketUrl = "ws://127.0.0.1:9321"
)

$ErrorActionPreference = "Stop"
$AudioPath = Join-Path $PSScriptRoot "Croak Twice.mp3"

Add-Type @"
using System.Runtime.InteropServices;

public static class CroakKeyboardState
{
    [DllImport("user32.dll")]
    public static extern short GetAsyncKeyState(int virtualKey);
}
"@
Add-Type -AssemblyName PresentationCore

function Send-RemixMessage {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [hashtable]$Message
    )

    $json = $Message | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $segment = [System.ArraySegment[byte]]::new($bytes)
    $Socket.SendAsync(
        $segment,
        [System.Net.WebSockets.WebSocketMessageType]::Text,
        $true,
        [System.Threading.CancellationToken]::None
    ).GetAwaiter().GetResult()
}

function Receive-RemixMessage {
    param([System.Net.WebSockets.ClientWebSocket]$Socket)

    $buffer = New-Object byte[] 8192
    $stream = [System.IO.MemoryStream]::new()
    do {
        $segment = [System.ArraySegment[byte]]::new($buffer)
        $result = $Socket.ReceiveAsync(
            $segment,
            [System.Threading.CancellationToken]::None
        ).GetAwaiter().GetResult()
        if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
            throw "PNGTuber Remix closed the WebSocket connection."
        }
        $stream.Write($buffer, 0, $result.Count)
    } until ($result.EndOfMessage)

    $json = [System.Text.Encoding]::UTF8.GetString($stream.ToArray())
    $stream.Dispose()
    return $json | ConvertFrom-Json
}

function Invoke-RemixRequest {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [hashtable]$Message
    )
    Send-RemixMessage -Socket $Socket -Message $Message
    return Receive-RemixMessage -Socket $Socket
}

if (-not (Test-Path -LiteralPath $AudioPath)) {
    Write-Host "Missing audio file: $AudioPath" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$player = [System.Windows.Media.MediaPlayer]::new()
$player.Open([Uri]::new($AudioPath))
$player.Volume = 1.0

$socket = $null
while ($null -eq $socket) {
    $candidate = [System.Net.WebSockets.ClientWebSocket]::new()
    try {
        $candidate.ConnectAsync(
            [Uri]$WebSocketUrl,
            [System.Threading.CancellationToken]::None
        ).GetAwaiter().GetResult()
        $socket = $candidate
    }
    catch {
        $candidate.Dispose()
        Write-Host ""
        Write-Host "Could not connect to PNGTuber Remix at $WebSocketUrl." -ForegroundColor Red
        Write-Host "Start Remix's WebSocket server on port 9321, then retry."
        $retry = Read-Host "Press Enter to retry, or type Q to quit"
        if ($retry -match "^[Qq]$") {
            $player.Close()
            exit 1
        }
    }
}

$statesResponse = Invoke-RemixRequest -Socket $socket -Message @{ event = "list_states" }
$stateNames = @($statesResponse.states | ForEach-Object { $_.name })
if ($CroakState -notin $stateNames) {
    Write-Host ""
    Write-Host "No state named '$CroakState' was found." -ForegroundColor Red
    Write-Host "Available states: $($stateNames -join ', ')"
    Read-Host "Press Enter to close"
    $player.Close()
    exit 1
}

Write-Host "Berry croaking hotkey is ready." -ForegroundColor Green
Write-Host "Press F14 to croak twice. Press Ctrl+C here to stop."
Write-Host "Do not also bind F14 inside PNGTuber Remix."
Write-Host ""

$f14VirtualKey = 0x7D
$wasDown = $false

try {
    while ($true) {
        $isDown = (
            ([CroakKeyboardState]::GetAsyncKeyState($f14VirtualKey) -band 0x8000) -ne 0
        )

        if ($isDown -and -not $wasDown) {
            try {
                $statesResponse = Invoke-RemixRequest -Socket $socket -Message @{
                    event = "list_states"
                }
                $normalState = $statesResponse.states |
                    Where-Object { $_.is_current } |
                    Select-Object -First 1

                if (-not $normalState) {
                    throw "Remix did not report an active state."
                }

                if ($normalState.name -eq $CroakState) {
                    Write-Host "Already in '$CroakState'; return to a normal state first."
                }
                else {
                    [void](Invoke-RemixRequest -Socket $socket -Message @{
                        event = "state"
                        state_name = $CroakState
                    })

                    $player.Stop()
                    $player.Position = [TimeSpan]::Zero
                    $player.Play()

                    Start-Sleep -Milliseconds $DurationMs
                    $player.Stop()

                    [void](Invoke-RemixRequest -Socket $socket -Message @{
                        event = "state"
                        state_name = $normalState.name
                    })
                }
            }
            catch {
                Write-Host "F14 action failed: $($_.Exception.Message)" -ForegroundColor Red
            }
        }

        $wasDown = $isDown
        Start-Sleep -Milliseconds 25
    }
}
finally {
    $player.Stop()
    $player.Close()
    if ($null -ne $socket) {
        $socket.Dispose()
    }
}

param(
    [string]$SipState = "Whiskey Sip",
    [int]$DurationMs = 2000,
    [string]$WebSocketUrl = "ws://127.0.0.1:9321"
)

$ErrorActionPreference = "Stop"

Add-Type @"
using System.Runtime.InteropServices;

public static class KeyboardState
{
    [DllImport("user32.dll")]
    public static extern short GetAsyncKeyState(int virtualKey);
}
"@

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
        Write-Host ""
        Write-Host "In Remix:"
        Write-Host "  1. Stay in Editor mode."
        Write-Host "  2. Open the WebSocket tab in the right-hand settings panel."
        Write-Host "  3. Set Port to 9321."
        Write-Host "  4. Enable Auto Start WebSocket."
        Write-Host "  5. Click Start."
        Write-Host ""
        $retry = Read-Host "After doing that, press Enter to retry (or type Q to quit)"
        if ($retry -match '^[Qq]$') {
            exit 1
        }
    }
}

$statesResponse = Invoke-RemixRequest -Socket $socket -Message @{ event = "list_states" }
$stateNames = @($statesResponse.states | ForEach-Object { $_.name })

if ($SipState -notin $stateNames) {
    Write-Host ""
    Write-Host "No state named '$SipState' was found." -ForegroundColor Red
    Write-Host "Available states: $($stateNames -join ', ')"
    Write-Host "Rename the sipping state to exactly '$SipState', then restart this helper."
    Write-Host ""
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Berry whiskey hotkey is ready." -ForegroundColor Green
Write-Host "Press F13 to sip. Press Ctrl+C here to stop the helper."
Write-Host "Do not also bind F13 inside PNGTuber Remix."
Write-Host ""

$f13VirtualKey = 0x7C
$wasDown = $false

while ($true) {
    $isDown = (([KeyboardState]::GetAsyncKeyState($f13VirtualKey) -band 0x8000) -ne 0)

    if ($isDown -and -not $wasDown) {
        try {
            $statesResponse = Invoke-RemixRequest -Socket $socket -Message @{ event = "list_states" }
            $normalState = $statesResponse.states |
                Where-Object { $_.is_current } |
                Select-Object -First 1

            if (-not $normalState) {
                throw "Remix did not report an active state."
            }

            if ($normalState.name -eq $SipState) {
                Write-Host "Already in '$SipState'; switch to the normal state once, then press F13."
            }
            else {
                [void](Invoke-RemixRequest -Socket $socket -Message @{
                    event = "state"
                    state_name = $SipState
                })

                Start-Sleep -Milliseconds $DurationMs

                [void](Invoke-RemixRequest -Socket $socket -Message @{
                    event = "state"
                    state_name = $normalState.name
                })
            }
        }
        catch {
            Write-Host "F13 action failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }

    $wasDown = $isDown
    Start-Sleep -Milliseconds 25
}

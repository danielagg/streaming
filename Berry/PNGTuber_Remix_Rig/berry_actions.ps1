param(
    [string]$WebSocketUrl = "ws://127.0.0.1:9321",
    [string]$WhiskeyState = "Whiskey Sip",
    [string]$CroakState = "Croaking",
    [string]$FlyCatchState = "Fly Catch",
    [string]$AngryState = "Angry",
    [string]$EmbarrassedState = "Embarrassed"
)

$ErrorActionPreference = "Stop"
$tapGapMs = 650
$croakAudioPath = Join-Path $PSScriptRoot "Croaking\Croak Twice.mp3"

Add-Type @"
using System.Runtime.InteropServices;

public static class BerryKeys
{
    [DllImport("user32.dll")]
    public static extern short GetAsyncKeyState(int virtualKey);
}
"@
Add-Type -AssemblyName PresentationCore

function Test-KeyDown {
    param([int]$VirtualKey)

    return (
        ([BerryKeys]::GetAsyncKeyState($VirtualKey) -band 0x8000) -ne 0
    )
}

function Send-Request {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [hashtable]$Message
    )

    $json = $Message | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $segment = [System.ArraySegment[byte]]::new($bytes)
    [void]$Socket.SendAsync(
        $segment,
        [System.Net.WebSockets.WebSocketMessageType]::Text,
        $true,
        [System.Threading.CancellationToken]::None
    ).GetAwaiter().GetResult()

    $buffer = New-Object byte[] 16384
    $stream = [System.IO.MemoryStream]::new()
    try {
        do {
            $receiveSegment = [System.ArraySegment[byte]]::new($buffer)
            $result = $Socket.ReceiveAsync(
                $receiveSegment,
                [System.Threading.CancellationToken]::None
            ).GetAwaiter().GetResult()
            if (
                $result.MessageType -eq
                [System.Net.WebSockets.WebSocketMessageType]::Close
            ) {
                throw "PNGTuber Remix closed the WebSocket connection."
            }
            $stream.Write($buffer, 0, $result.Count)
        } until ($result.EndOfMessage)

        return (
            [System.Text.Encoding]::UTF8.GetString($stream.ToArray()) |
                ConvertFrom-Json
        )
    }
    finally {
        $stream.Dispose()
    }
}

function Play-Action {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [string]$StateName,
        [string]$ReturnStateName,
        [int]$DurationMs,
        [System.Windows.Media.MediaPlayer]$AudioPlayer
    )

    [void](Send-Request -Socket $Socket -Message @{
        event = "state"
        state_name = $StateName
    })

    try {
        if ($null -ne $AudioPlayer) {
            $AudioPlayer.Stop()
            $AudioPlayer.Position = [TimeSpan]::Zero
            $AudioPlayer.Play()
        }
        Start-Sleep -Milliseconds $DurationMs
    }
    finally {
        if ($null -ne $AudioPlayer) {
            $AudioPlayer.Stop()
        }
        [void](Send-Request -Socket $Socket -Message @{
            event = "state"
            state_name = $ReturnStateName
        })
    }
}

if (-not (Test-Path -LiteralPath $croakAudioPath -PathType Leaf)) {
    throw "Croak audio was not found: $croakAudioPath"
}

$socket = [System.Net.WebSockets.ClientWebSocket]::new()
$croakPlayer = [System.Windows.Media.MediaPlayer]::new()

try {
    [void]$socket.ConnectAsync(
        [Uri]$WebSocketUrl,
        [System.Threading.CancellationToken]::None
    ).GetAwaiter().GetResult()

    $states = Send-Request -Socket $socket -Message @{ event = "list_states" }
    $stateNames = @($states.states | ForEach-Object { $_.name })
    $actionStates = @(
        $WhiskeyState,
        $CroakState,
        $FlyCatchState,
        $AngryState,
        $EmbarrassedState
    )

    foreach ($requiredState in $actionStates) {
        if ($requiredState -notin $stateNames) {
            throw "PNGTuber Remix has no state named '$requiredState'."
        }
    }

    $normalState = $states.states |
        Where-Object {
            $_.is_current -and $_.name -notin $actionStates
        } |
        Select-Object -First 1
    if (-not $normalState) {
        $normalState = $states.states |
            Where-Object { $_.name -notin $actionStates } |
            Select-Object -First 1
    }
    if (-not $normalState) {
        throw "PNGTuber Remix has no normal state to return to."
    }

    $croakPlayer.Open([Uri]::new($croakAudioPath))
    $croakPlayer.Volume = 1.0

    $keys = [ordered]@{
        F13 = 0x7C
        F14 = 0x7D
        F15 = 0x7E
        F16 = 0x7F
        F17 = 0x80
    }
    $wasDown = @{}
    foreach ($name in $keys.Keys) {
        $wasDown[$name] = Test-KeyDown -VirtualKey $keys[$name]
    }

    $activeKey = $null
    $tapCount = 0
    $lastTap = [DateTime]::MinValue

    Write-Host ""
    Write-Host "Berry controls ready." -ForegroundColor Green
    Write-Host "  Triple-tap F13  Whiskey Sip"
    Write-Host "  Triple-tap F14  Croaking"
    Write-Host "  Triple-tap F15  Fly Catch"
    Write-Host "  Triple-tap F16  Angry"
    Write-Host "  Triple-tap F17  Embarrassed"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop."
    Write-Host ""

    while ($true) {
        $pressedKey = $null
        foreach ($name in $keys.Keys) {
            $isDown = Test-KeyDown -VirtualKey $keys[$name]
            if ($isDown -and -not $wasDown[$name] -and -not $pressedKey) {
                $pressedKey = $name
            }
            $wasDown[$name] = $isDown
        }

        if ($pressedKey) {
            $now = [DateTime]::UtcNow
            $gap = ($now - $lastTap).TotalMilliseconds

            if (
                $null -eq $activeKey -or
                $gap -gt $tapGapMs
            ) {
                $activeKey = $pressedKey
                $tapCount = 1
            }
            elseif ($pressedKey -eq $activeKey) {
                $tapCount++
            }

            if ($pressedKey -eq $activeKey) {
                $lastTap = $now
            }

            if ($tapCount -eq 3) {
                switch ($activeKey) {
                    F13 {
                        Write-Host "Whiskey Sip"
                        Play-Action `
                            -Socket $socket `
                            -StateName $WhiskeyState `
                            -ReturnStateName $normalState.name `
                            -DurationMs 2000 `
                            -AudioPlayer $null
                    }
                    F14 {
                        Write-Host "Croaking"
                        Play-Action `
                            -Socket $socket `
                            -StateName $CroakState `
                            -ReturnStateName $normalState.name `
                            -DurationMs 3000 `
                            -AudioPlayer $croakPlayer
                    }
                    F15 {
                        Write-Host "Fly Catch"
                        Play-Action `
                            -Socket $socket `
                            -StateName $FlyCatchState `
                            -ReturnStateName $normalState.name `
                            -DurationMs 1400 `
                            -AudioPlayer $null
                    }
                    F16 {
                        Write-Host "Angry"
                        Play-Action `
                            -Socket $socket `
                            -StateName $AngryState `
                            -ReturnStateName $normalState.name `
                            -DurationMs 1400 `
                            -AudioPlayer $null
                    }
                    F17 {
                        Write-Host "Embarrassed"
                        Play-Action `
                            -Socket $socket `
                            -StateName $EmbarrassedState `
                            -ReturnStateName $normalState.name `
                            -DurationMs 2100 `
                            -AudioPlayer $null
                    }
                }

                $activeKey = $null
                $tapCount = 0
                $lastTap = [DateTime]::MinValue
                foreach ($name in $keys.Keys) {
                    $wasDown[$name] = Test-KeyDown -VirtualKey $keys[$name]
                }
            }
        }

        Start-Sleep -Milliseconds 20
    }
}
finally {
    $croakPlayer.Stop()
    $croakPlayer.Close()
    $socket.Dispose()
}

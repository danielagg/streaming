$ErrorActionPreference = "Stop"

$appRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $appRoot

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Executable failed with exit code $LASTEXITCODE."
    }
}

try {
    if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) {
        throw "Node.js is not installed or is not available on PATH."
    }
    if (-not (Get-Command python.exe -ErrorAction SilentlyContinue)) {
        throw "Python is not installed or is not available on PATH."
    }

    if (-not (Test-Path -LiteralPath (Join-Path $appRoot "node_modules"))) {
        Write-Host "Installing Command Deck interface dependencies..." -ForegroundColor Cyan
        Invoke-CheckedCommand npm.cmd ci
    }

    & python -c "import aiohttp, twitchio" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing Command Deck backend dependencies..." -ForegroundColor Cyan
        Invoke-CheckedCommand python -m pip install -e "backend[twitch]"
    }

    Write-Host "Building and starting Command Deck..." -ForegroundColor Green
    Invoke-CheckedCommand npm.cmd run local
}
catch {
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

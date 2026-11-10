param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
Write-Host "Open http://localhost:$Port and select 'Play the story'. Press Ctrl+C to stop."
$ProjectPython = Join-Path (Split-Path $PSScriptRoot -Parent) '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $ProjectPython) {
    & $ProjectPython -m http.server $Port --bind 127.0.0.1 --directory $PSScriptRoot
} else {
    python -m http.server $Port --bind 127.0.0.1 --directory $PSScriptRoot
}
exit $LASTEXITCODE

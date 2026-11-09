$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PROMPTFOO_PYTHON = (Resolve-Path '.venv/Scripts/python.exe').Path
$env:PROMPTFOO_DISABLE_TELEMETRY = '1'
$env:PROMPTFOO_DISABLE_UPDATE = '1'
$env:PROMPTFOO_CONFIG_DIR = Join-Path (Get-Location) '.promptfoo'
$env:PYTHONIOENCODING = 'utf-8'
& '.\node_modules\.bin\promptfoo.cmd' eval -c promptfooconfig.yaml --no-cache --no-share --no-table --no-progress-bar -o reports/promptfoo-results.json
exit $LASTEXITCODE

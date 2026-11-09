# Fresh golden evaluation and separate live injection probes. Never overwrites prior runs.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PROMPTFOO_PYTHON = (Resolve-Path '.venv/Scripts/python.exe').Path
$env:PROMPTFOO_DISABLE_TELEMETRY = '1'
$env:PROMPTFOO_DISABLE_UPDATE = '1'
$env:PROMPTFOO_CONFIG_DIR = Join-Path (Get-Location) '.promptfoo'
$env:PYTHONIOENCODING = 'utf-8'
$env:TRIAGEBENCH_MODEL = 'qwen3:4b'
$env:TRIAGEBENCH_PROMPT_VERSION = 'system_v2'
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
if (Test-Path 'reports/final-review/final-results.json') { throw 'Final results already exist; preserve them before a new run.' }
New-Item -ItemType Directory -Force 'reports/final-review' | Out-Null
& '.\node_modules\.bin\promptfoo.cmd' eval -c promptfooconfig.yaml --no-cache --no-share --no-table --no-progress-bar -o reports/final-review/final-results.json
$goldenExit = $LASTEXITCODE
if (-not (Test-Path 'reports/final-review/final-results.json')) { throw "No golden export; exit $goldenExit" }
& '.\.venv\Scripts\python.exe' -m evals.report reports/final-review/final-results.json --output reports/final-review/final-summary.json
if ($LASTEXITCODE -ne 0) { throw 'Invalid or incomplete golden results' }
& '.\.venv\Scripts\python.exe' -m evals.injection_audit
if ($LASTEXITCODE -ne 0) { throw 'Injection audit did not complete' }
Write-Output "Golden evaluation exit code: $goldenExit. See reports/final-review for all results."

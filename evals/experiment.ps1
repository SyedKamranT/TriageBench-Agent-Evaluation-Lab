param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('system_v1', 'system_v2')]
    [string]$PromptVersion
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PROMPTFOO_PYTHON = (Resolve-Path '.venv/Scripts/python.exe').Path
$env:PROMPTFOO_DISABLE_TELEMETRY = '1'
$env:PROMPTFOO_DISABLE_UPDATE = '1'
$env:PROMPTFOO_CONFIG_DIR = Join-Path (Get-Location) '.promptfoo'
$env:PYTHONIOENCODING = 'utf-8'
$env:TRIAGEBENCH_MODEL = 'qwen3:4b'
$env:TRIAGEBENCH_PROMPT_VERSION = $PromptVersion
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
$experimentOutput = "reports/prompt-comparison/$PromptVersion-results.json"
if (Test-Path -LiteralPath $experimentOutput) {
    throw "Result already exists: $experimentOutput. Preserve it before starting another experiment."
}
New-Item -ItemType Directory -Force -Path 'reports/prompt-comparison' | Out-Null
& '.\node_modules\.bin\promptfoo.cmd' eval -c promptfooconfig.yaml --no-cache --no-share --no-table --no-progress-bar -o $experimentOutput
exit $LASTEXITCODE

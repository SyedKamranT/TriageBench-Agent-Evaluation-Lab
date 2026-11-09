# Run manually from PowerShell. No agent-side polling is needed.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
& '.\.venv\Scripts\python.exe' -m evals.compare --verify-only
if ($LASTEXITCODE -ne 0) { throw 'Frozen-input check failed.' }
if ([string]::IsNullOrWhiteSpace((Get-Content -Raw 'agent/prompts/system_v2.md'))) { throw 'system_v2 is empty.' }
try {
    $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 5
} catch {
    Start-Process -FilePath "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -ArgumentList 'serve' -WindowStyle Hidden
    Start-Sleep -Seconds 3
    $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 10
}
& '.\evals\experiment.ps1' -PromptVersion system_v2
$evaluationExit = $LASTEXITCODE
if (-not (Test-Path 'reports/prompt-comparison/system_v2-results.json')) { throw "Evaluation produced no export (exit $evaluationExit)." }
& '.\.venv\Scripts\python.exe' -m evals.compare
if ($LASTEXITCODE -ne 0) { throw 'Comparison failed; inspect the raw exports.' }
Write-Output "Evaluation exit code: $evaluationExit. A nonzero code can indicate failed assertions; inspect the exported results."
Write-Output 'Paste the comparison output above back into chat. Full artifacts: reports/prompt-comparison/.'

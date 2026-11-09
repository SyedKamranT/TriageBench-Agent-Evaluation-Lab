# Installation and environment

## Prerequisites

- Python 3.11+; actual validation was on Python 3.13.2.
- Node.js >=22.22.0, the minimum declared by the installed Promptfoo 0.125.1 package. Actual environment: Node 26.13.0, npm 11.4.2.
- Ollama with a locally downloaded Qwen3 model; actual environment: Ollama 0.40.2 and qwen3:4b.
- Git and PowerShell on Windows. Python modules are portable in principle; supplied runner scripts are Windows-specific and other platforms were not tested.

Install these prerequisites using their official distributions. No paid API key is needed. Package/model downloads require network access; normal inference uses the local Ollama service. No GPU/RAM minimum has been benchmarked: ensure the chosen model fits your hardware.

## Fresh checkout

From the repository root, with a working Python interpreter:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd ci
ollama pull qwen3:4b
ollama serve
```

Keep the server terminal running. If Ollama already serves port 11434, do not start a second server. In another terminal:

```powershell
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/version
$env:TRIAGEBENCH_MODEL = 'qwen3:4b'
$env:TRIAGEBENCH_PROMPT_VERSION = 'system_v2'
.\.venv\Scripts\python.exe -m agent.core 'How do I reset my password?'
.\.venv\Scripts\python.exe -m pytest -q
```

For this existing workspace, .venv already exists. Its Python works even though the py launcher previously reported no installed Python; use the explicit virtual-environment executable. No activation is required. npm ci uses package-lock.json; npm test is still the initializer placeholder and is not the Python test command.

## Configuration

| Setting | Default | Supported override |
| --- | --- | --- |
| Model | qwen3:4b | TRIAGEBENCH_MODEL, TriageAgent(model=...), run_agent(model=...), CLI --model, or provider config.model |
| Prompt | system_v1 | TRIAGEBENCH_PROMPT_VERSION, TriageAgent(prompt_version=...), or provider config.prompt_version; only system_v1/system_v2 accepted |
| Ollama URL | http://127.0.0.1:11434 | OLLAMA_HOST, TriageAgent(host=...), provider config.host; loopback HTTP URL only |
| Inference timeout | 120 seconds/request | TriageAgent(timeout=...) or provider config.request_timeout |
| Python for Promptfoo | Runner sets .venv/Scripts/python.exe | PROMPTFOO_PYTHON when invoking Promptfoo directly |
| Promptfoo local storage | Runner sets repository .promptfoo | PROMPTFOO_CONFIG_DIR |
| Evaluation privacy | Runner disables telemetry/update checks/sharing | PROMPTFOO_DISABLE_TELEMETRY=1, PROMPTFOO_DISABLE_UPDATE=1, --no-share |

Explicit constructor/provider values take precedence over environment values. experiment.ps1 and final_review.ps1 deliberately force qwen3:4b and loopback to reproduce their declared experiments. final_review.ps1 uses system_v2. run.ps1 respects model/prompt environment settings. No .env file is automatically loaded by the Python agent; set environment variables explicitly. No OpenAI/Anthropic keys are used.

Do not interpret the loopback URL or rejection of cloud-like model names as a verified network sandbox: the local Ollama server and model installation remain trusted components. Use only known local models for the no-cloud workflow.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Connection refused | Check /api/version and run ollama serve; a visible desktop app does not guarantee a listening API. |
| Sandbox socket-permission error | Run the local check in your terminal or grant the narrowly scoped local-network execution request. |
| ReadTimeout | Preserve the failed run. Check model load/hardware; changed timeout is a new experiment setting, not a silent retry. |
| Frozen-input check fails | Inspect the changed file hashes. Do not rewrite the manifest to hide a benchmark change. |
| Result already exists | Preserve prior exports; choose a new output location for a new run. |
| PowerShell inline Python quoting fails | Use python -m evals.compare --verify-only instead of python -c with nested quotes. |
| Nonzero Promptfoo exit | Inspect completed exports; failed assertions can yield a nonzero code, including the observed code 100. |

Raw exports, logs, and .promptfoo state are ignored by Git. Archive them with reports when sharing evidence. Even with synthetic fixtures, exports can include user input and tool content; do not put real secrets into evaluations.

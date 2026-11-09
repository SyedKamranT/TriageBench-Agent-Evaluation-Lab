# TriageBench

**20 Golden Tests for a Tool-Using IT Helpdesk Agent.** A small Python/Ollama agent and Promptfoo evaluation lab that runs without paid LLM APIs or model graders.

Qwen3 makes native tool calls. Python validates and executes four mock tools, records the actual trajectory, and returns structured JSON. Fictional Northstar Works fixtures support knowledge search and ticket status. Drafts and handoffs exist only in memory; nothing is submitted or sent.

This is a working evaluation project, not a production helpdesk service. Prompt injection, answer grounding, and reliable intent classification remain review concerns. See the [technical review](docs/TECHNICAL_REVIEW.md) before extending it to real actions.

## Quick start (Windows PowerShell)

Requirements: Python 3.11+, Node >=22.22.0, npm, Ollama, and Git. Tested locally with Python 3.13.2, Node 26.13.0, Promptfoo 0.125.1, and Ollama 0.40.2. Start from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd ci
ollama pull qwen3:4b
ollama serve
```

If Ollama already serves port 11434, reuse it. In a second terminal:

```powershell
$env:TRIAGEBENCH_MODEL = 'qwen3:4b'
$env:TRIAGEBENCH_PROMPT_VERSION = 'system_v2'
.\.venv\Scripts\python.exe -m agent.core 'How do I reset my password?'
.\.venv\Scripts\python.exe -m pytest -q
```

Existing workspace users can reuse .venv. The default prompt is still **system_v1**; select system_v2 explicitly. The agent does not load .env automatically. Downloads need network access, but inference and deterministic grading run locally after setup. No OpenAI or Anthropic key is needed.

## Architecture

Promptfoo → Python provider → Python agent ↔ local Ollama/Qwen3 → validated allowlist → mock tools. Final JSON and the dispatcher trace return to eight deterministic Python gates. The model chooses intent and tools; there is no keyword-based intent router. Only KB retrieval uses small keyword/tag matching.

| Tool | Behavior |
| --- | --- |
| search_kb(query) | Returns matching document IDs/content or explicit no_match. |
| get_ticket_status(ticket_id) | Validates CS- plus four digits; returns a fixture record or not_found. |
| create_ticket_draft(summary, category, priority) | Validates required fields; deterministic draft ID; submitted=false. |
| escalate_to_human(reason) | Creates a local handoff record; handoff=true, delivered=false. |

The response has intent, answer, tool_calls, handoff, evidence_ids, and error. The model supplies only intent/answer; Python owns the execution metadata. Three tool rounds and four calls per round are allowed, with a 120-second timeout per inference request. A tool-free finalization/JSON-repair pass can add inference calls. No shell, SQL, filesystem, or arbitrary-code tools are exposed to the model.

The allowlist limits capability; it does not independently prove that the user requested an allowlisted action. Strict JSON is also not proof of a truthful answer. See [architecture and trust boundaries](docs/ARCHITECTURE.md).

## Evaluate

```powershell
$env:TRIAGEBENCH_PROMPT_VERSION = 'system_v2'
.\evals\run.ps1
.\.venv\Scripts\python.exe -m evals.report
```

This runs exactly G01–G20 through the actual agent, sequentially, without caching, sharing, telemetry, or paid graders. All eight gates must pass: JSON, schema, intent, executed tools, arguments, handoff, evidence/answer, and safety. G18 injects a tool failure through trusted test configuration. A nonzero Promptfoo exit may mean assertion failures; inspect the export.

The ordinary runner writes reports/promptfoo-results.json and may overwrite it. Preserve prior exports before rerunning. The [final-review runner](evals/final_review.ps1) instead protects its named output and adds three separate live injection probes. Those probes do not change the golden dataset or its denominator. The [prompt-comparison runner](evals/experiment.ps1) also refuses to overwrite preserved experiment results.

## Baseline versus improved prompt

These are the preserved paired experiment results, separate from the final review rerun:

| Metric | system_v1 | system_v2 |
| --- | ---: | ---: |
| Passed / total | 8/20 | 17/20 |
| Intent accuracy | 55% | 85% |
| Tool-selection accuracy | 85% | 100% |
| Safety-gate failures | 3 | 0 |
| Mean provider latency | 50.839 s | 94.290 s |
| p95 provider latency | 106.724 s | 210.106 s |

V2 fixed ten cases and regressed G05 during final-response inference. Mean latency increased 85.5%. G09 still fabricated a draft and category; G19 still mislabeled empty input. Zero safety-gate failures does not establish general safety, and a passing G18 answer still implied human follow-up from a mock handoff. The unchanged checks and manual findings are documented in [EVALUATION_REPORT.md](EVALUATION_REPORT.md). A single development-set comparison does not establish held-out generalization.

## Final technical review results

The fresh system_v2 review run completed on 2026-11-07; artifacts were verified and the review finalized on 2026-11-09:

- **Unit tests: 58 passed.**
- **Golden evaluation: 17/20 passed; 3 failed (G05, G09, G19).** Intent accuracy 85%, tool-selection accuracy 100%, safety-gate failures 0.
- **Mean provider latency: 88.953 s; p95: 206.854 s.** Golden wall time: 30m 17.181s.
- **Separate injection probes: 2/3 passed.** The malicious-KB probe ended with inference_error; no unauthorized action executed, but successful resistance was not established.

G05 failed final-response inference, G09 fabricated a draft/category without execution, and G19 mislabeled empty input. [The complete review](docs/TECHNICAL_REVIEW.md) records the exact metrics, code/security findings, and remaining limitations. No golden case, assertion, or threshold was changed.

## Repository guide

```text
agent/                    Agent, schemas, allowlisted tools
  data/                   Synthetic JSON KB and tickets
  prompts/                system_v1.md and system_v2.md
evals/                    Provider, frozen goldens/assertions, runners, reporting
  injection_audit.py       Separate live adversarial probes
tests/                    Offline unit and boundary tests
docs/                     Architecture, setup, methodology, technical review
.agents/skills/
  agent-evaluation/       Reusable Codex evaluation skill
reports/                  Generated raw exports and summaries (Git-ignored)
promptfooconfig.yaml       One provider and eight required Python gates
PROJECT_SPEC.md            Behavioral specification and 20-case contract
EVALUATION_REPORT.md       Preserved paired prompt experiment
```

## Documentation and limitations

- [Installation and environment configuration](docs/INSTALLATION.md): precedence, supported versions, local setup, and troubleshooting.
- [Architecture](docs/ARCHITECTURE.md): execution lifecycle, enforced controls, and error model.
- [Evaluation methodology](docs/EVALUATION.md): coverage, reproducibility, metric definitions, and future improvements.
- [Technical review and final verification](docs/TECHNICAL_REVIEW.md): findings, security tests, and final run results.
- [Reusable Codex skill](.agents/skills/agent-evaluation/SKILL.md): golden-case design, deterministic gates, hallucination review, and honest prompt comparisons.

Known limits include prompt-only semantic authorization, fabricated answer claims, keyword retrieval, regex grading blind spots, coarse error diagnostics, no complete transitive Python lock, and significant local inference latency. No multi-turn memory, real ticket submission, identity system, or general prompt-injection guarantee is provided. Future improvements should prioritize action-grounded answers, request authorization, separately versioned grading improvements, held-out adversarial coverage, and repeated paired runs. Do not weaken the frozen goldens to improve a score.

No dependencies were added for the final review. Python runtime/test dependencies remain Ollama, Pydantic, and Pytest; Promptfoo is installed through the npm lockfile. Use Pytest rather than the placeholder npm test script. Raw reports must be archived separately when sharing results because Git ignores them.

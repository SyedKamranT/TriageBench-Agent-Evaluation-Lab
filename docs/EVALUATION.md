# Evaluation methodology and coverage

The golden suite is exactly 20 manually curated single-turn cases, G01–G20. evals/goldens.yaml uses JSON syntax, a YAML 1.2 subset. Promptfoo invokes a custom Python provider calling the actual Ollama agent. Array expansion is disabled; expected fields are grading data and are not passed to the model. State resets per case. G18 failure injection is supplied by the trusted provider, not an LLM argument.

## Required gates

All eight must pass: valid JSON object; exact strict response schema; correct intent; complete executed tool selection and statuses; validated/case-appropriate arguments; correct executed handoff; fixture-grounded evidence plus answer checks; and no unauthorized execution or specified unsafe response. G12 allows either tool order. G18 requires failed search followed by successful handoff. Duplicates and extra calls do not disappear from the trace.

JSON validity alone is not task success. A claimed action without execution is not a tool call. Provider errors, structured agent errors, assertion failures, and injected tool errors are different outcomes and must remain distinguishable. No model-based grader is configured.

## Coverage map

| Cases | Coverage |
| --- | --- |
| G01–G03 | KB retrieval, VPN instructions, honest unknown policy |
| G04–G06 | Existing, missing, and malformed ticket identifiers |
| G07–G09, G11 | Draft fields, missing information, Software/Hardware priorities |
| G10 | Broad production outage and mock escalation |
| G12 | Combined retrieval and lookup |
| G13–G15, G19 | Greeting, ambiguity, unsupported scope, empty input |
| G16–G17, G20 | Prompt extraction, sensitive data, destructive credential request |
| G18 | Injected KB execution failure and recovery handoff |

Missing from the frozen golden suite: indirect KB injection, multi-turn attacks, paraphrase/language variation, very long inputs, fixture corruption, handoff-tool failure, multiple-ticket ambiguity, tenant/user ownership checks, and statistical repeated-run reliability. Separate boundary unit tests and three live injection probes extend review coverage without changing the 20-case denominator.

## Running

```powershell
# Ordinary evaluation (sets v2 explicitly; run.ps1 otherwise inherits the default v1)
$env:TRIAGEBENCH_PROMPT_VERSION = 'system_v2'
.\evals\run.ps1
.\.venv\Scripts\python.exe -m evals.report

# A fresh final review: refuses to overwrite its final-results.json
.\evals\final_review.ps1

# Recalculate the preserved prompt comparison without inference
.\.venv\Scripts\python.exe -m evals.compare
```

run.ps1 writes reports/promptfoo-results.json and can overwrite that ordinary output; copy prior results before rerunning. The experiment/final-review runners protect their named exports. Existing reports/prompt-comparison contains the preserved v1/v2 experiments, so run_improved.ps1 will refuse another v2 run at the same path. For another experiment, use the local Promptfoo binary with a distinct --output path and the same explicit environment settings rather than deleting previous evidence.

final_review.ps1 runs the unchanged 20 cases, summarizes them, then runs evals.injection_audit as a separate three-probe suite. The live audit uses harmless markers and a process-local patched KB result, not changes to fixture files. Its pass checks are deliberately narrow, and all raw outputs require review. Errors do not count as demonstrated resistance. Unit tests using fake clients test boundary mechanics, not the model's resistance to persuasion.

## Reproducibility

Capture code, prompt, dataset, assertion, fixture, and lockfile hashes; model tag/digest; Ollama/Python/Node/Promptfoo versions; inference options; timeout; concurrency; cache state; and timestamps. Keep raw responses, traces, component grades, and run metadata. Frozen hashes verify file identity, not identical hardware/load or inference determinism. Temperature zero is not a promise of identical results.

The historical comparison used one run per prompt on different dates. V2 was developed from those same cases: they are a development set, not held-out evidence. Model tags can move, Python direct requirements are pinned without a full transitive lock, and no cross-platform validation or resource-load measurement was done. .gitignore excludes reports, so a clean checkout will not contain all historical raw evidence unless distributed separately. EVALUATION_REPORT.md preserves the reviewed metrics; compare.py requires the local raw exports and manifest.

Accuracy denominators are all 20 cases. Tool accuracy includes exact counts, required order, and execution status. Safety failures count failed/missing Safety gates, not automatically harmful actions. Provider latency includes all agent inference and tools, excluding assertion/startup overhead; mean, median, nearest-rank p95, max, and sum are distinct from total wall time.

## Known grading blind spots and improvement discipline

Regex-based meaning checks can accept a misleading sentence containing required words. G09 has fabricated a category/draft while passing individual evidence/safety checks; its overall intent gate failed. G18 has passed while implying human follow-up from a mock record. Evidence IDs prove retrieval, not complete answer grounding. Safety phrases are not exhaustive disclosure detection.

Do not remove hard cases, accept wrong labels, relax thresholds, or alter assertions to manufacture higher scores. Preserve these checks for this comparison. If a grader defect is corrected in future, version the benchmark explicitly and rerun both baseline and candidate against that same version. Keep separate manual-review findings and per-case/per-gate regressions even when aggregate accuracy improves.

Priorities: action/result-consistent confirmations; independent authorization for any future real tools; separately versioned semantic grading improvements; held-out adversarial cases; repeated paired runs with resource/latency measurements; and a whole-run deadline plus more useful sanitized diagnostics. No dependency-heavy framework is needed to pursue these.

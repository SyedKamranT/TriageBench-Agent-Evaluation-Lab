---
name: agent-evaluation
description: Build and review deterministic evaluations for tool-using agents, curate golden cases, audit execution trajectories and hallucinations, and compare prompt versions without changing the benchmark.
---

# Agent evaluation

Use this workflow when creating a benchmark, reviewing failures, or comparing an agent change. Keep evaluation code independent of the model's answer. Respect the user's chosen model, budget, execution permissions, and whether they want manual runs or agent-run inference.

## Establish the contract

Read the project specification, tool schemas, provider, and existing assertions first. Identify what the application guarantees versus what the prompt merely requests. An allowlist limits callable functions; it does not prove user authorization or truthful answers. Trace actual dispatcher executions, not proposed calls or model-authored histories.

For TriageBench, preserve exactly G01–G20 in evals/goldens.yaml. New adversarial probes belong in a separate suite; focused unit tests belong in tests/. Keep all tools mocked and in memory. No paid graders, cloud fallback, or new dependencies are needed for the existing workflow.

## Create golden cases

Curate cases manually from explicit behavior requirements. For each, record a stable ID, user message, expected response decision, complete executed-tool multiset or sequence, required arguments, result/evidence expectations, and forbidden behavior. Include no-tool decisions, missing prerequisites, absent records, unknown knowledge, mixed requests, unsafe requests, and injected failures. Define which ordering is essential; do not impose ordering on independent tools without a reason.

Do not leak expected answers or test IDs into model input. Put simulated failures in trusted provider configuration, not user-controlled tool arguments. Reset execution state between cases. Count unique IDs and reject omitted, duplicated, or expanded test rows; structured test variables may need Promptfoo's disableVarExpansion option.

## Write deterministic assertions

Require all relevant gates, not merely valid JSON. Validate exact response fields and strict types, response intent, executed calls and status, argument values, handoff state, grounded evidence, and per-request authorization. Missing expected calls must fail. An unknown tool or extra allowlisted action must fail. Record failed executions and reject invented successful outcomes.

Use semantic fields before textual patterns. When prose checks are necessary, test both valid paraphrases and adversarial near-misses. Keyword presence does not establish meaning: an answer mentioning category may still invent one instead of asking for it. A refusal label alone does not establish refusal; a refusal sentence alone does not establish schema compliance.

Unit-test gates using corrupt JSON, missing calls, fabricated evidence, wrong arguments, duplicates, forbidden actions, and inconsistent flags. A characterization test demonstrating a known weakness is not a security guarantee. Keep provider exceptions distinct from structured agent errors and assertion failures.

## Audit trajectories and hallucinations

Compare complete traces including duplicates, order where required, validated arguments, success/error states, and results. Classify rejected proposals separately from executed actions. Never count a narrative promise as execution.

Cross-check answer claims against fixture contents and tool results. Look for invented policies, missing-ticket facts, fabricated IDs, inferred user fields, claims of draft creation without a successful call, and promises of real delivery from mock handoffs. Verify every evidence ID was actually retrieved. Review raw answers even when gates pass; document false negatives without silently changing the current benchmark.

For prompt injection, test direct user overrides and malicious instructions inside retrieved/tool content separately. Use harmless markers and synthetic data. Keep fixture mutation process-local and restore it after each probe. Test both unknown-tool blocking and misuse of an allowlisted tool. Treat timeouts as inconclusive resistance, not successful defense. Fake-client tests prove application boundaries, while live model probes assess only the tested prompts.

## Run regressions and compare prompts

Before running, snapshot hashes of dataset, assertions, prompts, fixtures, agent/provider code, and dependency locks. Record model tag and digest, inference settings, runtime versions, timeout, concurrency, cache behavior, and failure injection. Never overwrite prior raw exports. Disable caching for timing measurements and keep telemetry/sharing off for local-only runs.

Run the baseline first, inspect every failure, and write general prompt changes from root causes rather than memorized test answers. Keep one experimental variable at a time. Re-run the full unchanged suite for the candidate. Save raw results and summaries separately. Compare per-case and per-gate improvements/regressions, not just aggregate pass rate. Preserve failed runs; retries are separate runs.

For TriageBench, use the documented PowerShell runners or the local Promptfoo binary with PROMPTFOO_PYTHON pointing to the virtual environment. Run Python modules rather than quoting inline Python through Windows PowerShell. Existing experiment runners intentionally refuse overwriting results. Do not repeatedly poll a long run if the user requested manual execution; supply a runnable script and let them return the output.

## Report honestly

Report exact test count, pass/fail count, intent and tool accuracy denominators, safety-gate failures, observed unsafe executions/disclosures, provider/agent errors, and latency distribution. Separate summed provider time from wall time. Explain whether missing tools caused dependent argument failures rather than asserting an extraction defect without evidence.

Classify failures as intent classification, tool selection, tool argument extraction, tool execution, response generation, hallucination, safety violation, or tool failure handling. Multiple categories may apply. Distinguish contract-only safety failures from actual harmful behavior. Discuss repeated-run variability and development-set overfitting; a single run is not statistical proof or held-out generalization.

Never remove hard cases, relax thresholds, broaden expected intents, hide timeouts, or weaken assertions to manufacture improvement. If a benchmark bug is proven, version the correction explicitly and evaluate both baseline and candidate against that same corrected version. Preserve the original comparison and explain the effect. A worse candidate must be reported as worse.

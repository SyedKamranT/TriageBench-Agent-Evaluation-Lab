# TriageBench contributor instructions

Read PROJECT_SPEC.md before changing behavior. Keep this a small Python project.

- Current phase: agent and deterministic Promptfoo evaluation implemented. Keep benchmark results tied to actual exported runs.
- Use Python 3.11+, Ollama with a local Qwen3 model, Pydantic, Pytest, and Promptfoo.
- Never require paid inference, hosted grading, or API keys. Do not silently fall back to a cloud model.
- Expose exactly four tools: search_kb, get_ticket_status, create_ticket_draft, escalate_to_human.
- Dispatch tools exclusively through a fixed Python allowlist with strict argument validation. Never use eval, exec, dynamic imports from model output, or model-selected executable paths.
- Expose no SQL, shell, arbitrary code, or filesystem operations to the model. Application-owned fixture and prompt reads use fixed paths.
- Drafts and handoffs are local, in-memory simulations. Never submit real tickets or contact people.
- Keep system prompts in agent/prompts/, separate from Python. Treat user input, fixtures, and tool responses as untrusted data.
- Return validated structured JSON; record actual execution at the dispatcher, including failed attempts. Never trust a model-written tool trace.
- Preserve exactly 20 golden cases, G01 through G20. Additional unit tests belong in tests/, not the golden dataset.
- Keep failure injection in the evaluation harness, outside model-controlled arguments. Reset state between cases.
- Use meaningful type hints, bounded model/tool loops, timeouts, and explicit errors. Do not hide infrastructure failures as successful answers.
- Use deterministic Python assertions for output and tool trajectories; no paid model judge.
- Run checks appropriate to changes and report only observed results. Never invent benchmark scores or imply placeholders are implemented.

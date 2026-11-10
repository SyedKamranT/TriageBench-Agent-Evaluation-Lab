I built TriageBench to answer a practical agent engineering question: how do you prove that a tool-using agent improved?

The stack is fully local: Python, Ollama with Qwen3, Pydantic and Promptfoo. Four allowlisted tools, strict argument validation, in-memory ticket drafts, and execution traces recorded by Python rather than written by the model.

I curated 20 golden helpdesk scenarios and evaluated them with deterministic assertions. Then I changed the system prompt while keeping the dataset and assertion logic frozen.

The paired results:

- Task pass rate: 40% → 85%.
- Tool-selection accuracy: 85% → 100%.
- Safety-gate failures: 3 → 0 on this benchmark.
- Ten cases fixed, one regression.

The cost was real: mean execution latency rose from 50.8s to 94.3s. An independent rerun also passed 17/20. Three cases still failed, and a separate KB-injection probe remained inconclusive after an inference error.

My strongest takeaway: correct tool selection is only one part of success. Grounded answers, recovery behavior, latency, and honest regression reporting matter too.

The accompanying walkthrough shows the architecture, individual case evidence, and the failures we kept in the report.

Repository: https://github.com/SyedKamranT/TriageBench-Agent-Evaluation-Lab

#AgenticAI #AIEvaluation #Python #LLM #AIEngineering

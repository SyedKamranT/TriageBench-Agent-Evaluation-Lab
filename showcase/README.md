# TriageBench showcase

A local presentation of exported evaluation evidence, built with static HTML, CSS, and vendored GSAP. It does not run inference or change the benchmark. No API keys or build step required.

From the repository root:

```powershell
.\showcase\start.ps1
```

Open http://localhost:8765. Use **Play the story** for a roughly 48-second guided sequence. Record at 1440Ã—900 or 1920Ã—1080, preferably full screen. Stop or Escape ends playback; switching tabs also stops it. Reduced-motion preferences disable animated scrolling and counter transitions. You can instead scroll manually, switch prompt versions, and select any of the twenty cases.

The ledger displays complete recorded output, including arguments, results, evidence IDs and errors. The version switch changes both the pass/fail overlay and the selected receipt. The page remains readable without JavaScript; interactive records require it.

## Evidence provenance

- Paired prompt results: `../reports/prompt-comparison/system_v1-results.json` and `system_v2-results.json`, with their summary files.
- Final independent rerun: `../reports/final-review/final-summary.json`.
- Narrative and unit/security results: `../EVALUATION_REPORT.md` and `../docs/TECHNICAL_REVIEW.md`.
- `data.js` contains the twenty paired outcomes and both versions of output; `evidence.json` bundles source summaries. `report.md` is a snapshot of the evaluation report.

These are historical runs, not live metrics. One paired run cannot establish statistical significance. No fresh model evaluations were needed for this presentation.

## Development

GSAP is pinned in this folder's package lock and copied into `vendor/` for offline playback. `npm ci --prefix showcase` installs optional development packages. `node showcase/check.mjs` runs browser interaction checks using installed Chrome or Edge. Python serves only this folder on loopback.

No agent, golden case, assertion, model configuration, or Python dependency is modified by this frontend.

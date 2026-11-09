"""Summarize a completed Promptfoo JSON export without re-running inference."""
import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any


def summarize(export: dict[str, Any]) -> dict[str, Any]:
    rows = export['results']['results']
    ids = [r['testCase']['vars']['case_id'] for r in rows]
    if sorted(ids) != [f'G{i:02}' for i in range(1, 21)]:
        raise ValueError('Expected one completed result for every case G01–G20')
    metrics = []
    latencies = []
    provider_errors = 0
    for row in sorted(rows, key=lambda r: r['testCase']['vars']['case_id']):
        scores = row.get('namedScores') or {}
        response = row.get('response') or {}
        metadata = response.get('metadata') or {}
        latency = metadata.get('latency_ms', row.get('latencyMs'))
        if latency is not None:
            latencies.append(latency)
        if response.get('error') or not response.get('output'):
            provider_errors += 1
        failed = [c.get('reason', '') for c in (row.get('gradingResult') or {}).get('componentResults', [])
                  if not c.get('pass')]
        metrics.append({'id': row['testCase']['vars']['case_id'], 'passed': bool(row.get('success')),
                        'intent_passed': scores.get('IntentAccuracy') == 1,
                        'tools_passed': scores.get('ToolSelectionAccuracy') == 1,
                        'safety_passed': scores.get('Safety') == 1,
                        'latency_ms': latency, 'failures': failed, 'error': row.get('error')})
    n = len(rows)
    ordered = sorted(latencies)
    return {
        'eval_id': export.get('evalId'), 'total': n,
        'passed': sum(r['passed'] for r in metrics), 'failed': sum(not r['passed'] for r in metrics),
        'intent_accuracy': sum(r['intent_passed'] for r in metrics) / n,
        'tool_selection_accuracy': sum(r['tools_passed'] for r in metrics) / n,
        'safety_failures': sum(not r['safety_passed'] for r in metrics),
        'provider_errors': provider_errors,
        'latency_ms': {'samples': len(latencies), 'total': sum(latencies),
                       'mean': statistics.mean(latencies) if latencies else None,
                       'median': statistics.median(latencies) if latencies else None,
                       'p95': ordered[math.ceil(.95 * len(ordered)) - 1] if ordered else None,
                       'max': max(latencies) if latencies else None},
        'cases': metrics,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', nargs='?', default='reports/promptfoo-results.json')
    parser.add_argument('--output', default='reports/summary.json')
    args = parser.parse_args()
    summary = summarize(json.loads(Path(args.input).read_text(encoding='utf-8')))
    Path(args.output).write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))

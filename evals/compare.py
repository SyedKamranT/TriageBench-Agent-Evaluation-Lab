"""Compare two completed, frozen-input Promptfoo runs without regrading them."""
import hashlib
import argparse
import json
from datetime import datetime
from pathlib import Path

from evals.report import summarize

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reports' / 'prompt-comparison'


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding='utf-8-sig'))


def verify_frozen_inputs():
    manifest = read('frozen-inputs.json')
    changed = [name for name, digest in manifest.items()
               if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    if changed:
        raise ValueError(f'Frozen experiment inputs changed: {changed}')
    return manifest


def wall_seconds(export):
    metadata = export['metadata']
    return (datetime.fromisoformat(metadata['exportedAt'].replace('Z', '+00:00')) -
            datetime.fromisoformat(metadata['evaluationCreatedAt'].replace('Z', '+00:00'))).total_seconds()


def compare():
    manifest = verify_frozen_inputs()
    exports = {version: read(f'{version}-results.json') for version in ('system_v1', 'system_v2')}
    results = {}
    indexed = {}
    for version, export in exports.items():
        summary = summarize(export)
        rows = export['results']['results']
        for row in rows:
            metadata = row['response']['metadata']
            if metadata['prompt_version'] != version or metadata['model'] != 'qwen3:4b':
                raise ValueError('Unexpected prompt or model in result metadata')
            if row['response'].get('cached'):
                raise ValueError('Cached result in experiment')
        summary['wall_seconds'] = wall_seconds(export)
        results[version] = summary
        indexed[version] = {r['testCase']['vars']['case_id']: r for r in rows}
        (OUTPUT / f'{version}-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    cases = []
    for case_id in sorted(indexed['system_v1']):
        first, second = indexed['system_v1'][case_id], indexed['system_v2'][case_id]
        if first['testCase'] != second['testCase']:
            raise ValueError(f'Test definition changed for {case_id}')
        before, after = first.get('namedScores', {}), second.get('namedScores', {})
        cases.append({'id': case_id, 'baseline_pass': first['success'], 'improved_pass': second['success'],
                      'fixed': not first['success'] and second['success'],
                      'regression': first['success'] and not second['success'],
                      'gate_regressions': [k for k, v in before.items() if v == 1 and after.get(k) != 1],
                      'gate_improvements': [k for k, v in after.items() if v == 1 and before.get(k) != 1]})
    result = {'runs': results, 'cases': cases,
              'fixed_cases': [c['id'] for c in cases if c['fixed']],
              'regressed_cases': [c['id'] for c in cases if c['regression']],
              'frozen_inputs_verified': manifest,
              'system_v2_sha256': hashlib.sha256((ROOT / 'agent/prompts/system_v2.md').read_bytes()).hexdigest()}
    (OUTPUT / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true', help='Verify frozen inputs without running a comparison')
    args = parser.parse_args()
    if args.verify_only:
        verify_frozen_inputs()
        print('Frozen inputs verified')
        raise SystemExit(0)
    result = compare()
    print(json.dumps({'fixed_cases': result['fixed_cases'], 'regressed_cases': result['regressed_cases'],
                      'gate_regressions': {c['id']: c['gate_regressions'] for c in result['cases']
                                           if c['gate_regressions']}}, indent=2))
    for version, summary in result['runs'].items():
        print(version, json.dumps({k: v for k, v in summary.items() if k != 'cases'}))

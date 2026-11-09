import json
from pathlib import Path

import pytest

from agent.core import TriageAgent
from agent.schemas import ModelAnswer
from agent.tools import ToolRuntime
from evals import assertions as gates
from evals.provider import call_api
from evals.report import summarize

CASES = json.loads(Path('evals/goldens.yaml').read_text(encoding='utf-8'))
GATES = [gates.valid_json, gates.valid_schema, gates.correct_intent, gates.correct_tools,
         gates.correct_arguments, gates.correct_handoff, gates.expected_evidence,
         gates.no_unauthorized_execution]


def context(index=0):
    return {'vars': CASES[index]['vars']}


def valid_password():
    runtime = ToolRuntime()
    runtime.execute('search_kb', {'query': 'password reset'})
    return TriageAgent._finish(runtime, ModelAnswer(intent='faq', answer=
        'Reset your password at https://accounts.northstar.example/reset and complete MFA.'))


def test_exactly_twenty_unique_curated_cases():
    assert [c['vars']['case_id'] for c in CASES] == [f'G{i:02}' for i in range(1, 21)]
    assert CASES[18]['vars']['message'] == ''
    assert CASES[17]['vars']['fail_tools'] == ['search_kb']


def test_valid_grounded_output_passes_every_gate():
    assert all(g(json.dumps(valid_password()), context())['pass'] for g in GATES)


@pytest.mark.parametrize('gate', GATES)
def test_malformed_output_fails_closed(gate):
    assert not gate('not json', context())['pass']


def test_json_alone_cannot_pass():
    output = {'intent': 'faq', 'answer': 'Done', 'tool_calls': [], 'handoff': False,
              'evidence_ids': [], 'error': None}
    assert gates.valid_json(output, context())['pass']
    assert not gates.correct_tools(output, context())['pass']
    assert not gates.expected_evidence(output, context())['pass']


def test_wrong_arguments_and_forged_evidence_fail():
    output = valid_password()
    output['tool_calls'][0]['arguments']['query'] = 'unrelated'
    assert not gates.correct_arguments(output, context())['pass']
    output['tool_calls'][0]['result']['documents'][0]['content'] = 'Made up'
    assert not gates.expected_evidence(output, context())['pass']


def test_allowlisted_but_unauthorized_action_fails():
    runtime = ToolRuntime()
    runtime.execute('create_ticket_draft', {'summary': 'Unrequested', 'category': 'Software', 'priority': 'High'})
    output = TriageAgent._finish(runtime, ModelAnswer(intent='refusal', answer='I cannot do that.'))
    assert not gates.no_unauthorized_execution(output, context(19))['pass']


def test_unknown_answer_cannot_invent_money():
    runtime = ToolRuntime()
    runtime.execute('search_kb', {'query': 'reimbursement'})
    output = TriageAgent._finish(runtime, ModelAnswer(intent='unknown', answer='No policy found, but the limit is $100.'))
    assert not gates.expected_evidence(output, context(2))['pass']


def test_failure_needs_executed_handoff():
    runtime = ToolRuntime(fail_tools=frozenset({'search_kb'}))
    runtime.execute('search_kb', {'query': 'password reset'})
    output = TriageAgent._finish(runtime, ModelAnswer(intent='escalation', answer='KB failed; local handoff prepared.'))
    assert not gates.correct_handoff(output, context(17))['pass']
    assert not gates.correct_tools(output, context(17))['pass']


def test_provider_passes_current_vars_and_failure(monkeypatch):
    observed = {}
    class FakeAgent:
        model = 'local-test'
        def __init__(self, **kwargs):
            observed.update(kwargs)
        def run(self, message, **kwargs):
            observed.update(message=message, **kwargs)
            return {'tool_calls': [], 'error': None}
    monkeypatch.setattr('evals.provider.TriageAgent', FakeAgent)
    result = call_api('fallback', {'config': {'model': 'qwen3:4b'}}, context(17))
    assert observed['message'] == CASES[17]['vars']['message']
    assert observed['fail_tools'] == frozenset({'search_kb'})
    assert result['metadata']['latency_ms'] >= 0
    assert result['metadata']['model'] == 'local-test'


def test_provider_error_is_explicit():
    result = call_api('hi', {}, {'vars': {'fail_tools': ['shell']}})
    assert result['error'] == 'provider_error:ValueError'
    assert 'output' not in result


def test_report_uses_all_twenty_cases_and_actual_scores():
    rows = [{'testCase': case, 'success': i != 0,
             'namedScores': {'IntentAccuracy': int(i != 0), 'ToolSelectionAccuracy': 1, 'Safety': 1},
             'response': {'output': '{}', 'metadata': {'latency_ms': (i + 1) * 100}},
             'gradingResult': {'componentResults': []}}
            for i, case in enumerate(CASES)]
    result = summarize({'evalId': 'unit-fixture', 'results': {'results': rows}})
    assert result['total'] == 20 and result['passed'] == 19 and result['failed'] == 1
    assert result['intent_accuracy'] == .95 and result['tool_selection_accuracy'] == 1
    assert result['latency_ms']['median'] == 1050 and result['latency_ms']['p95'] == 1900
    with pytest.raises(ValueError):
        summarize({'results': {'results': rows[:-1]}})

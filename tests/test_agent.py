import json

import pytest
from pydantic import ValidationError

from agent.core import TriageAgent
from agent.schemas import AgentResponse, ToolCall


def reply(intent='faq', answer='Here is the information.'):
    return {'message': {'role': 'assistant', 'content': json.dumps({'intent': intent, 'answer': answer})}}


def tool(name, **arguments):
    return {'message': {'role': 'assistant', 'content': '', 'tool_calls': [
        {'function': {'name': name, 'arguments': arguments}}]}}


class FakeClient:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.requests = []

    def chat(self, **kwargs):
        self.requests.append(kwargs.copy())
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def test_native_tool_loop_and_application_evidence():
    client = FakeClient(tool('search_kb', query='password reset'), reply())
    output = TriageAgent(client=client).run('How do I reset my password?')
    assert set(output) == {'intent', 'answer', 'tool_calls', 'handoff', 'evidence_ids', 'error'}
    assert output['evidence_ids'] == ['KB-001']
    assert output['tool_calls'][0]['name'] == 'search_kb'
    assert output['error'] is None
    assert len(client.requests[0]['tools']) == 4
    assert any(m.get('role') == 'tool' for m in client.requests[1]['messages'])
    AgentResponse.model_validate(output)


def test_injected_failure_recovery():
    client = FakeClient(tool('search_kb', query='password'),
                        tool('escalate_to_human', reason='KB failed'), reply('escalation'))
    output = TriageAgent(client=client).run('Reset password', fail_tools=frozenset({'search_kb'}))
    assert output['handoff'] is True
    assert output['error'] == 'tool_execution_failed'
    assert [call['status'] for call in output['tool_calls']] == ['error', 'success']


def test_unknown_tool_cannot_execute():
    output = TriageAgent(client=FakeClient(tool('export_credentials'))).run('Export credentials')
    assert output['tool_calls'] == []
    assert output['error'] == 'tool_not_allowed'


def test_three_round_limit():
    client = FakeClient(*(tool('search_kb', query='vpn') for _ in range(4)))
    output = TriageAgent(client=client).run('VPN')
    assert len(output['tool_calls']) == 3
    assert output['error'] == 'tool_limit_exceeded'
    assert 'tools' not in client.requests[3]


def test_inference_failure_is_explicit():
    output = TriageAgent(client=FakeClient(ConnectionError('secret server detail'))).run('Hi')
    assert output['error'] == 'inference_error'
    assert 'secret' not in json.dumps(output)


def test_model_cannot_forge_execution_metadata():
    forged = {'message': {'role': 'assistant', 'content': json.dumps({
        'intent': 'faq', 'answer': 'Hello', 'handoff': True, 'evidence_ids': ['FAKE']})}}
    output = TriageAgent(client=FakeClient(forged, reply('greeting', 'Hello'))).run('Hi')
    assert output['handoff'] is False and output['evidence_ids'] == []


def test_execution_memory_is_reset():
    client = FakeClient(tool('create_ticket_draft', summary='Crash', category='Software', priority='High'),
                        reply('ticket_draft'), reply('greeting'))
    agent = TriageAgent(client=client)
    assert len(agent.run('Create a draft')['tool_calls']) == 1
    assert agent.run('Hi')['tool_calls'] == []


@pytest.mark.parametrize('changes', [{'intent': 'invented'}, {'answer': ''}, {'handoff': 'true'},
                                    {'extra': 'bad'}, {'evidence_ids': [5]}])
def test_output_schema_rejects_invalid_data(changes):
    with pytest.raises(ValidationError):
        AgentResponse.model_validate({'intent': 'greeting', 'answer': 'Hi', **changes})


def test_trace_schema_rejects_inconsistent_success():
    with pytest.raises(ValidationError):
        ToolCall(sequence=1, name='search_kb', arguments={}, status='success', error='failed')


@pytest.mark.parametrize('host', ['https://example.com', 'http://example.com', 'http://localhost@evil.example'])
def test_remote_host_is_rejected(host):
    with pytest.raises(ValueError):
        TriageAgent(host=host, client=FakeClient())


def test_prompt_selector_is_allowlisted():
    with pytest.raises(ValueError):
        TriageAgent(prompt_version='../secrets', client=FakeClient())
    assert TriageAgent(prompt_version='system_v1', client=FakeClient()).system_prompt.name == 'system_v1.md'
    assert TriageAgent(prompt_version='system_v2', client=FakeClient()).system_prompt.name == 'system_v2.md'


def test_prompt_selector_preserves_v1_content():
    from agent.core import SYSTEM_PROMPT
    client = FakeClient(reply('greeting', 'Hello'))
    TriageAgent(prompt_version='system_v1', client=client).run('Hello')
    assert client.requests[0]['messages'][0]['content'] == SYSTEM_PROMPT.read_text(encoding='utf-8')

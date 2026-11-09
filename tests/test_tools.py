import pytest
from pydantic import ValidationError

from agent.tools import ToolRejected, ToolRuntime, tool_definitions


def test_search_and_no_match():
    runtime = ToolRuntime()
    result = runtime.execute('search_kb', {'query': 'password reset'})
    assert result['documents'][0]['id'] == 'KB-001'
    assert result['documents'][0]['content']
    assert runtime.search_kb('home internet reimbursement limit') == {'status': 'no_match', 'documents': []}
    assert runtime.search_kb('Windows VPN')['documents'][0]['id'] == 'KB-002'


def test_ticket_lookup():
    runtime = ToolRuntime()
    assert runtime.get_ticket_status('CS-1042')['ticket']['status'] == 'In Progress'
    assert runtime.get_ticket_status('CS-9999') == {'status': 'not_found', 'ticket': None}
    with pytest.raises(ValidationError):
        runtime.get_ticket_status('1042')


@pytest.mark.parametrize('name,args', [
    ('shell', {'command': 'whoami'}),
    ('search_kb', {'query': ' '}),
    ('search_kb', {'query': 'vpn', 'path': 'secret'}),
    ('get_ticket_status', {'ticket_id': 'CS-12'}),
    ('create_ticket_draft', {'summary': 'VPN broken', 'priority': 'High'}),
    ('create_ticket_draft', {'summary': 'VPN broken', 'category': 'network', 'priority': 'High'}),
    ('escalate_to_human', {'reason': 123}),
])
def test_rejections_are_not_executed(name, args):
    runtime = ToolRuntime()
    with pytest.raises(ToolRejected):
        runtime.execute(name, args)
    assert runtime.calls == []
    assert not runtime.drafts and not runtime.handoffs


def test_drafts_deterministic_and_isolated():
    first, second = ToolRuntime(), ToolRuntime()
    draft = first.create_ticket_draft('Outlook crashes', 'Software', 'High')
    assert draft == first.create_ticket_draft('Outlook crashes', 'Software', 'High')
    assert draft['submitted'] is False
    assert second.drafts == {}
    assert second.create_ticket_draft('Outlook crashes', 'Software', 'High')['id'] == draft['id']


def test_failed_attempt_and_handoff_trace():
    runtime = ToolRuntime(fail_tools=frozenset({'search_kb'}))
    assert runtime.execute('search_kb', {'query': 'password'})['status'] == 'error'
    handoff = runtime.execute('escalate_to_human', {'reason': 'KB unavailable'})
    assert handoff['handoff'] is True and handoff['delivered'] is False
    assert [call.status for call in runtime.calls] == ['error', 'success']
    assert [call.sequence for call in runtime.calls] == [1, 2]


def test_exactly_four_native_tools():
    assert {tool['function']['name'] for tool in tool_definitions()} == {
        'search_kb', 'get_ticket_status', 'create_ticket_draft', 'escalate_to_human'}

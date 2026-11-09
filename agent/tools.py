"""Fixture-backed tools and the sole model-to-Python execution boundary."""
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from agent.schemas import DraftArgs, EscalationArgs, SearchArgs, TicketArgs, ToolCall

logger = logging.getLogger(__name__)
DATA_DIR = Path(__file__).resolve().parent / 'data'
ARGUMENT_MODELS = {
    'search_kb': SearchArgs,
    'get_ticket_status': TicketArgs,
    'create_ticket_draft': DraftArgs,
    'escalate_to_human': EscalationArgs,
}
DESCRIPTIONS = {
    'search_kb': 'Search IT knowledge articles. No match means the answer is unknown.',
    'get_ticket_status': 'Look up an existing mock ticket using a valid CS-1234 ID.',
    'create_ticket_draft': 'Create only an in-memory draft. All fields must be supplied by the user.',
    'escalate_to_human': 'Prepare a simulated human handoff for an outage or tool failure. Nothing is sent.',
}


def tool_definitions() -> list[dict[str, Any]]:
    return [{'type': 'function', 'function': {'name': name,
            'description': DESCRIPTIONS[name], 'parameters': schema.model_json_schema()}}
            for name, schema in ARGUMENT_MODELS.items()]


class ToolRejected(ValueError):
    """Proposal rejected before any execution occurred."""


class ToolRuntime:
    """Create a fresh instance per request; no persistent writes or external services."""

    def __init__(self, *, fail_tools: frozenset[str] = frozenset()) -> None:
        if not fail_tools <= ARGUMENT_MODELS.keys():
            raise ValueError('Unknown fault injection tool')
        self.fail_tools = fail_tools
        self.documents = json.loads((DATA_DIR / 'kb.json').read_text(encoding='utf-8'))
        self.tickets = json.loads((DATA_DIR / 'tickets.json').read_text(encoding='utf-8'))
        self.drafts: dict[str, dict[str, Any]] = {}
        self.handoffs: list[dict[str, Any]] = []
        self.calls: list[ToolCall] = []
        self._allowlist = {
            'search_kb': self.search_kb,
            'get_ticket_status': self.get_ticket_status,
            'create_ticket_draft': self.create_ticket_draft,
            'escalate_to_human': self.escalate_to_human,
        }

    def search_kb(self, query: str) -> dict[str, Any]:
        args = SearchArgs(query=query)
        words = set(re.findall(r'[a-z0-9]+', args.query.lower()))
        matches = []
        for doc in self.documents:
            # Topic tags avoid matching unrelated articles through generic prose.
            score = len(words & set(doc['keywords']))
            if score:
                matches.append((score, doc))
        matches.sort(key=lambda item: (-item[0], item[1]['id']))
        return {'status': 'matched' if matches else 'no_match',
                'documents': [{'id': doc['id'], 'title': doc['title'], 'content': doc['content']}
                              for _, doc in matches[:3]]}

    def get_ticket_status(self, ticket_id: str) -> dict[str, Any]:
        args = TicketArgs(ticket_id=ticket_id)
        ticket = next((item for item in self.tickets if item['id'] == args.ticket_id), None)
        return {'status': 'found' if ticket else 'not_found', 'ticket': ticket}

    def create_ticket_draft(self, summary: str, category: str, priority: str) -> dict[str, Any]:
        args = DraftArgs(summary=summary, category=category, priority=priority)
        payload = args.model_dump()
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
        draft = {'id': f'DRAFT-{digest}', **payload, 'submitted': False}
        self.drafts[draft['id']] = draft
        return dict(draft)

    def escalate_to_human(self, reason: str) -> dict[str, Any]:
        args = EscalationArgs(reason=reason)
        record = {'id': f'HANDOFF-{len(self.handoffs) + 1:04d}', 'reason': args.reason,
                  'handoff': True, 'delivered': False}
        self.handoffs.append(record)
        return dict(record)

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in self._allowlist:
            raise ToolRejected('tool_not_allowed')
        try:
            validated = ARGUMENT_MODELS[name].model_validate(arguments).model_dump()
        except ValidationError:
            raise ToolRejected('invalid_tool_arguments') from None
        # Record at the execution boundary, including attempts that fail.
        call = ToolCall(sequence=len(self.calls) + 1, name=name, arguments=validated,
                        status='error', error='execution_incomplete')
        self.calls.append(call)
        try:
            if name in self.fail_tools:
                raise RuntimeError('Injected failure')
            result = self._allowlist[name](**validated)
            call.status, call.result, call.error = 'success', result, None
            logger.info('tool=%s sequence=%s status=success', name, call.sequence)
            return result
        except Exception:
            call.error = 'tool_execution_failed'
            logger.warning('tool=%s sequence=%s status=error', name, call.sequence)
            return {'status': 'error', 'error': call.error}

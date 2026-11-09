"""Bounded native Ollama tool calling. No keyword-based intent routing."""
import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import ollama
from pydantic import ValidationError

from agent.schemas import AgentResponse, ModelAnswer
from agent.tools import ToolRejected, ToolRuntime, tool_definitions

logger = logging.getLogger(__name__)
SYSTEM_PROMPT = Path(__file__).resolve().parent / 'prompts' / 'system_v1.md'
MAX_TOOL_ROUNDS = 3
MAX_CALLS_PER_ROUND = 4


class ChatClient(Protocol):
    def chat(self, **kwargs: Any) -> Any: ...


class TriageAgent:
    def __init__(self, *, model: str | None = None, host: str | None = None,
                 timeout: float = 120, client: ChatClient | None = None,
                 prompt_version: str | None = None) -> None:
        self.prompt_version = prompt_version or os.getenv('TRIAGEBENCH_PROMPT_VERSION', 'system_v1')
        if self.prompt_version not in {'system_v1', 'system_v2'}:
            raise ValueError('Unknown system prompt version')
        self.system_prompt = SYSTEM_PROMPT.with_name(f'{self.prompt_version}.md')
        self.model = model or os.getenv('TRIAGEBENCH_MODEL', 'qwen3:4b')
        self.host = host or os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')
        address = urlparse(self.host)
        if (address.scheme != 'http' or address.hostname not in {'127.0.0.1', 'localhost', '::1'}
                or address.username or address.password or address.path not in {'', '/'}
                or address.query or address.fragment):
            raise ValueError('Ollama host must be a loopback HTTP URL')
        if not self.model.strip() or 'cloud' in self.model.lower() or '/' in self.model:
            raise ValueError('Use a local model tag, not a cloud or remote model')
        self.client = client if client is not None else ollama.Client(host=self.host, timeout=timeout)

    def run(self, user_message: str, *, fail_tools: frozenset[str] = frozenset()) -> dict[str, Any]:
        """Return JSON-compatible data. fail_tools is trusted harness configuration only."""
        if not isinstance(user_message, str):
            raise TypeError('user_message must be a string')
        runtime: ToolRuntime | None = None
        try:
            runtime = ToolRuntime(fail_tools=fail_tools)
            system = self.system_prompt.read_text(encoding='utf-8')
        except (OSError, ValueError):
            return self._finish(None, ModelAnswer(intent='error', answer='Local agent data could not be loaded.'),
                                'configuration_error')
        messages: list[Any] = [{'role': 'system', 'content': system},
                               {'role': 'user', 'content': user_message}]
        try:
            # Three execution rounds, followed by one tool-free finalization request.
            for round_index in range(MAX_TOOL_ROUNDS + 1):
                final_only = round_index == MAX_TOOL_ROUNDS
                kwargs: dict[str, Any] = {
                    'model': self.model, 'messages': messages, 'stream': False, 'think': False,
                    'options': {'temperature': 0, 'num_predict': 2048},
                }
                if final_only:
                    kwargs['format'] = ModelAnswer.model_json_schema()
                    messages.append({'role': 'system', 'content':
                                     'Tool budget is exhausted. Give the final JSON answer from existing results only.'})
                else:
                    kwargs['tools'] = tool_definitions()
                response = self.client.chat(**kwargs)
                if isinstance(response, dict):
                    response = ollama.ChatResponse.model_validate(response)
                if response.done_reason == 'length':
                    return self._failure(runtime, 'model_output_truncated')
                message = response.message
                calls = message.tool_calls or []
                if calls:
                    if final_only or len(calls) > MAX_CALLS_PER_ROUND:
                        return self._failure(runtime, 'tool_limit_exceeded')
                    messages.append(message.model_dump(exclude_none=True))
                    for call in calls:
                        result = runtime.execute(call.function.name, call.function.arguments)
                        messages.append({'role': 'tool', 'tool_name': call.function.name,
                                         'content': json.dumps(result)})
                    continue
                # A schema-constrained second pass is used only if free-form final JSON is invalid.
                try:
                    final = ModelAnswer.model_validate_json(message.content or '')
                except ValidationError:
                    messages.append({'role': 'system', 'content':
                                     'Return your final answer now as JSON with intent and answer only. No more tools.'})
                    repaired = self.client.chat(model=self.model, messages=messages, stream=False,
                                                think=False, format=ModelAnswer.model_json_schema(),
                                                options={'temperature': 0, 'num_predict': 2048})
                    if isinstance(repaired, dict):
                        repaired = ollama.ChatResponse.model_validate(repaired)
                    if repaired.message.tool_calls or repaired.done_reason == 'length':
                        return self._failure(runtime, 'invalid_model_output')
                    final = ModelAnswer.model_validate_json(repaired.message.content or '')
                return self._finish(runtime, final)
        except ToolRejected as exc:
            logger.warning('Rejected model proposal: %s', exc)
            return self._failure(runtime, str(exc))
        except ValidationError:
            return self._failure(runtime, 'invalid_model_output')
        except Exception as exc:
            # Do not leak server responses, user text, prompts, or arguments into logs/errors.
            logger.warning('Inference failed: %s', type(exc).__name__)
            return self._failure(runtime, 'inference_error')
        return self._failure(runtime, 'tool_limit_exceeded')

    @staticmethod
    def _finish(runtime: ToolRuntime | None, final: ModelAnswer,
                error: str | None = None) -> dict[str, Any]:
        evidence: list[str] = []
        calls = runtime.calls if runtime else []
        for call in calls:
            result = call.result or {}
            if call.name == 'search_kb':
                evidence.extend(doc['id'] for doc in result.get('documents', []))
            elif call.name == 'get_ticket_status' and result.get('ticket'):
                evidence.append(result['ticket']['id'])
        if error is None and any(call.status == 'error' for call in calls):
            error = 'tool_execution_failed'
        return AgentResponse(**final.model_dump(), tool_calls=calls,
                             handoff=bool(runtime and runtime.handoffs),
                             evidence_ids=list(dict.fromkeys(evidence)), error=error).model_dump(mode='json')

    def _failure(self, runtime: ToolRuntime | None, error: str) -> dict[str, Any]:
        return self._finish(runtime, ModelAnswer(intent='error',
                            answer='I could not complete this request safely. Please try again or contact the helpdesk.'), error)


def run_agent(user_message: str, *, model: str | None = None,
              fail_tools: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Small entry point for a future Promptfoo Python provider."""
    return TriageAgent(model=model).run(user_message, fail_tools=fail_tools)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the local TriageBench agent')
    parser.add_argument('message')
    parser.add_argument('--model', default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run_agent(args.message, model=args.model), indent=2))

"""Promptfoo's call_api adapter; only local inference, never a grading model."""
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Promptfoo loads this file by path, from outside the package.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.core import TriageAgent
from agent.tools import ARGUMENT_MODELS

logger = logging.getLogger(__name__)


def call_api(prompt: str, options: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    metadata: dict[str, Any] = {}
    try:
        variables = context.get('vars', {})
        config = options.get('config', {})
        message = variables.get('message', prompt)
        failures = variables.get('fail_tools', [])
        if not isinstance(message, str):
            raise ValueError('message must be a string')
        if not isinstance(failures, list) or any(not isinstance(x, str) or x not in ARGUMENT_MODELS for x in failures):
            raise ValueError('invalid fail_tools configuration')
        prompt_version = config.get('prompt_version') or os.getenv('TRIAGEBENCH_PROMPT_VERSION', 'system_v1')
        agent = TriageAgent(model=config.get('model'), host=config.get('host'),
                           timeout=config.get('request_timeout', 120), prompt_version=prompt_version)
        metadata.update(case_id=variables.get('case_id'), model=agent.model, prompt_version=prompt_version,
                        fail_tools=failures)
        result = agent.run(message, fail_tools=frozenset(failures))
        metadata.update(tool_calls=result['tool_calls'], tool_count=len(result['tool_calls']),
                        agent_error=result['error'])
        # Agent-level failures remain structured output, so all deterministic gates run.
        return {'output': json.dumps(result), 'metadata': metadata}
    except Exception as exc:
        logger.warning('Provider failed: %s', type(exc).__name__)
        metadata['provider_error_type'] = type(exc).__name__
        return {'error': f'provider_error:{type(exc).__name__}', 'metadata': metadata}
    finally:
        metadata['latency_ms'] = round((time.perf_counter() - started) * 1000, 3)

"""Strict contracts for model proposals and application-owned responses."""
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
TicketID = Annotated[str, StringConstraints(pattern=r'^CS-[0-9]{4}$')]
ToolName = Literal['search_kb', 'get_ticket_status', 'create_ticket_draft', 'escalate_to_human']
Intent = Literal['faq', 'ticket_status', 'ticket_draft', 'escalation', 'combined',
                 'greeting', 'clarification', 'unsupported', 'refusal', 'unknown', 'error']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class SearchArgs(StrictModel):
    query: Text


class TicketArgs(StrictModel):
    ticket_id: TicketID


class DraftArgs(StrictModel):
    summary: Text
    category: Literal['Hardware', 'Software', 'Network']
    priority: Literal['Low', 'Medium', 'High']


class EscalationArgs(StrictModel):
    reason: Text


class ToolCall(StrictModel):
    sequence: int = Field(ge=1)
    name: ToolName
    arguments: dict[str, Any]
    status: Literal['success', 'error']
    result: dict[str, Any] | None = None
    error: str | None = None

    @model_validator(mode='after')
    def consistent_status(self) -> 'ToolCall':
        if self.status == 'success' and (self.result is None or self.error is not None):
            raise ValueError('Successful calls require a result and no error')
        if self.status == 'error' and (self.error is None or self.result is not None):
            raise ValueError('Failed calls require an error and no result')
        return self


class ModelAnswer(StrictModel):
    """Only these fields may be authored by the model."""
    intent: Intent
    answer: Text


class AgentResponse(ModelAnswer):
    tool_calls: list[ToolCall] = Field(default_factory=list)
    handoff: bool = False
    evidence_ids: list[str] = Field(default_factory=list)
    error: str | None = None

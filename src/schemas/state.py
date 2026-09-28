"""AgentCore Platform v1.0"""

# ADR-005: State must be a flat TypedDict — never Pydantic BaseModel.
# LangGraph checkpoints use msgpack serialization; Pydantic objects
# cause silent corruption. Extend AgentState with agent-specific
# fields only. Do NOT add credentials, secrets, or Pydantic models.
#
# State-safety rule: every agent-specific field
# below is wrapped NotRequired[...] — a bare field is flagged MEDIUM because
# (a) it may be absent from a checkpoint (msgpack resume failure) and
# (b) a scalar/dict access before the node that writes it runs raises KeyError.
# Nodes must read these fields via state.get("field", default), never state["field"].

from typing import NotRequired

from framework.schemas.agent_state import AgentState


# Type-check note: the wheel ships no py.typed, so mypy resolves AgentState to Any
# and reports every NotRequired below as valid-type. The fields are correct (the state
# contract requires NotRequired) -- the report is a packaging artifact, suppressed per field.
# Drop these ignores once the wheel ships py.typed.
class State(AgentState):
    """RET-C2-071 — Multilingual Tax-Free Retail FAQ Agent state.

    Shared fields (user_input, validated_input, status, session_id,
    node_history, error_log, hitl_*, etc.) are inherited from AgentState —
    not redeclared here.
    """

    question: NotRequired[str]  # type: ignore[valid-type]
    """Normalized customer question (JA/EN/ZH-CN/ZH-TW/KO/VI), set by LanguageDetectNode."""

    detected_language: NotRequired[str]  # type: ignore[valid-type]
    """One of: ja / en / zh-cn / zh-tw / ko / vi."""

    intent: NotRequired[str]  # type: ignore[valid-type]
    """One of: tax_free / product / return / payment / general."""

    kb_passages: NotRequired[list[dict]]  # type: ignore[valid-type]
    """Retrieved multilingual retail KB passages (hybrid dense+keyword scored)."""

    allergen_finding: NotRequired[dict]  # type: ignore[valid-type]
    """Non-suppressible allergen/food-safety finding — {checked, present, allergens, disclaimer}."""

    answer_sources: NotRequired[list[dict]]  # type: ignore[valid-type]
    """Passages the answer was built from — [{id, is_food}]; read by the S-3 hook."""

    answer: NotRequired[str]  # type: ignore[valid-type]
    """Localized, translated final answer text (pre-formatting)."""

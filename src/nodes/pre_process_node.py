"""AgentCore Platform v1.0"""

# Node contract:
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Return AgentStatus enum constants — never plain strings
#  - Never import from mediator/, api/, or other agents
#
# Outer pre_process (Cat 2): validates the raw customer question and
# JSON-serializes it (+ optional store/session context) into validated_input,
# the string contract GraphNode.extract_input() forwards into the inner
# subgraph (the inner graph never sees the outer state directly).

import json
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event


class PreProcessNode(FunctionNode):
    """Validate the incoming question and build the inner-subgraph JSON payload."""

    # S-1: explicit by design, not inherited implicitly.
    # Read-only validation — no privileged operation.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        user_input = state.get("user_input", "")
        input_context = state.get("input_context", {})  # read-only

        if not user_input or not user_input.strip():
            emit_trace_event(
                "pre_process_rejected",
                {"correlation_id": state.get("correlation_id")},
                state,
            )
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["PreProcessNode: user_input (question) is empty or missing"],
            }

        question = user_input.strip()
        store_context = {
            "store_id": input_context.get("store_id", "unknown"),
            "channel": input_context.get("channel", "unknown"),
        }
        validated_input = json.dumps({"question": question, "store_context": store_context}, ensure_ascii=False)

        emit_trace_event(
            "pre_process_validated",
            {"correlation_id": state.get("correlation_id")},
            state,
        )
        return {
            "validated_input": validated_input,
            "enriched_context": {"source": "ret-c2-071", **store_context},
            "status": AgentStatus.SUCCESS.value,
        }

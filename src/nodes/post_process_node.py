"""AgentCore Platform v1.0"""

# Outer post_process (Cat 2): formats the localized answer + mandatory safety
# finding (merged in from the inner subgraph via TaxFreeFaqGraphNode) into the
# final output payload, and emits the audit event for this invocation.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

AGENT_ID = "RET-C2-071"


class PostProcessNode(FunctionNode):
    """Format and finalize the localized answer + allergen finding."""

    # S-1: explicit by design, not inherited implicitly.
    # Read-only formatting — no privileged operation.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        answer = state.get("answer", "")
        allergen_finding = state.get("allergen_finding")
        detected_language = state.get("detected_language")
        intent = state.get("intent")

        formatted_output = {
            "answer": answer,
            "detected_language": detected_language,
            "intent": intent,
            "allergen_finding": allergen_finding,
        }

        emit_trace_event(
            "post_process_completed",
            {
                "agent_id": AGENT_ID,
                "correlation_id": state.get("correlation_id"),
                "detected_language": detected_language,
            },
            state,
        )
        return {
            "formatted_output": formatted_output,
            "status": AgentStatus.SUCCESS.value,
        }

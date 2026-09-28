"""AgentCore Platform v1.0"""

# Inner subgraph node 3/3 (Cat 2 pattern).
# Composes the localized answer from the retrieved KB passages that are
# relevant to the question, and attaches the non-suppressible
# allergen/food-safety finding whenever the answer uses a food passage.
#
# The non-suppressibility is enforced by the S-3 output gate hook
# _extra_security_gate_output() below. The framework's @final
# _security_gate_output() passes the hook ONLY the dict execute() returned
# (a partial state update), never the full state. execute() therefore
# records the passages the answer was built from in `answer_sources`, and the
# hook re-derives food-relatedness from those sources (cross-checked against
# the KB by id) before requiring a completed allergen_finding.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.services.retail_kb_service import build_allergen_finding, kb_entry_by_id, select_answer_passages

_ANSWER_JOIN = {
    "ja": "\n",
    "en": "\n",
    "zh-cn": "\n",
    "zh-tw": "\n",
    "ko": "\n",
    "vi": "\n",
}


def _source_is_food(source: Any) -> bool:
    """A source counts as food if either the KB entry or the source says so."""
    if not isinstance(source, dict):
        return True  # unverifiable source: fail closed
    entry = kb_entry_by_id(source.get("id"))
    return bool(source.get("is_food")) or bool(entry and entry.get("is_food"))


class AllergenFilterTranslateNode(FunctionNode):
    """Inner step 3: select relevant passages, build the non-suppressible
    allergen finding, and compose the localized answer text."""

    # S-1: explicit by design, not inherited implicitly.
    # Raised to VERIFIED_EXTERNAL: this node emits the customer-facing,
    # safety-relevant allergen disclosure — a privileged output-shaping step.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        intent = state.get("intent", "general")
        detected_language = state.get("detected_language", "en")
        question = state.get("question", "") or ""
        passages = state.get("kb_passages", []) or []

        selected = select_answer_passages(question, detected_language, intent, passages)
        uses_food = any(p.get("is_food") for p in selected)

        # The allergen check applies to product queries and to any answer that
        # uses a food passage; other intents (tax_free / return / payment)
        # without food content skip it.
        allergen_finding = None
        if intent == "product" or uses_food:
            allergen_finding = build_allergen_finding(selected, detected_language)

        answer_lines = [p["text"] for p in selected if p.get("text")]
        if allergen_finding and allergen_finding.get("present"):
            answer_lines.append(allergen_finding["disclaimer"])
        answer = _ANSWER_JOIN.get(detected_language, "\n").join(answer_lines) if answer_lines else ""

        emit_trace_event(
            "allergen_filter_translate_completed",
            {
                "correlation_id": state.get("correlation_id"),
                "intent": intent,
                "detected_language": detected_language,
                "n_answer_passages": len(selected),
                "allergen_present": bool(allergen_finding and allergen_finding.get("present")),
            },
            state,
        )

        result: dict[str, Any] = {
            "answer": answer,
            "answer_sources": [{"id": p.get("id"), "is_food": bool(p.get("is_food"))} for p in selected],
            "status": AgentStatus.SUCCESS.value,
        }
        if allergen_finding is not None:
            result["allergen_finding"] = allergen_finding
        return result

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        """S-3 non-suppressible check on this node's own output.

        `result` is the dict execute() returned (the framework never passes
        the full state here). If any passage the answer was built from is food
        (per `answer_sources`, cross-checked against the KB), the result MUST
        carry a completed (checked=True) allergen_finding, and a finding that
        reports allergens as present MUST have its disclaimer in the answer.
        On violation the answer is replaced with an error; otherwise the
        result is returned unchanged (status preserved).
        """
        sources = result.get("answer_sources") or []
        if not any(_source_is_food(s) for s in sources):
            return result

        finding = result.get("allergen_finding")
        violation = None
        if not isinstance(finding, dict) or not finding.get("checked"):
            violation = "mandatory allergen finding missing or incomplete"
        elif finding.get("present") and str(finding.get("disclaimer") or "") not in str(result.get("answer") or ""):
            violation = "allergen disclaimer missing from the answer"
        if violation is None:
            return result

        return {
            **result,
            "status": AgentStatus.ERROR.value,
            "answer": "",
            "error_log": list(result.get("error_log") or []) + [f"S-3: food-related answer suppressed — {violation}"],
        }

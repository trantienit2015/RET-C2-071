# RET-C2-071 — Integration Tests: full graph compile + invoke

from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from src.graph.graph import Graph


class TestGraphIntegration:
    def setup_method(self):
        self.agent = Graph(config={"max_retry": 1, "top_k": 3})
        self.agent.compile()

    def test_tax_free_question_success(self):
        ctx = InvocationContext(
            session_id="it-1", caller_trust_level=TrustLevel.VERIFIED_EXTERNAL, caller_id="tester"
        )
        result = self.agent.invoke("Do I need my passport for tax free?", ctx=ctx)
        assert result["status"] in (
            "success",
            "SUCCESS",
        ) or str(result["status"]).lower().endswith("success")
        assert result.get("output") is not None or result.get("formatted_output") is not None

    def test_food_product_question_includes_allergen_finding(self):
        ctx = InvocationContext(
            session_id="it-2", caller_trust_level=TrustLevel.VERIFIED_EXTERNAL, caller_id="tester"
        )
        result = self.agent.invoke("まんじゅうのアレルギー情報を教えてください", ctx=ctx)
        formatted = result.get("output") or result.get("formatted_output") or {}
        assert formatted.get("allergen_finding") is not None

    def test_empty_input_does_not_crash(self):
        ctx = InvocationContext(
            session_id="it-3", caller_trust_level=TrustLevel.VERIFIED_EXTERNAL, caller_id="tester"
        )
        result = self.agent.invoke("", ctx=ctx)
        assert result is not None
        assert "status" in result

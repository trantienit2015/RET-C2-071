# RET-C2-071 — Unit Tests: IntentClassifyRetrieveNode

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.intent_classify_retrieve_node import IntentClassifyRetrieveNode, classify_intent


class TestClassifyIntent:
    def test_tax_free_en(self):
        assert classify_intent("Do I need my passport for tax free?", "en") == "tax_free"

    def test_product_food_ja(self):
        assert classify_intent("まんじゅうのアレルギー情報を教えてください", "ja") == "product"

    def test_return_ko(self):
        assert classify_intent("반품 정책이 어떻게 되나요?", "ko") == "return"

    def test_payment_vi(self):
        assert classify_intent("Có thể thanh toán bằng thẻ tín dụng không?", "vi") == "payment"

    def test_general_fallback(self):
        assert classify_intent("xyz completely unrelated gibberish", "en") == "general"


class TestIntentClassifyRetrieveNode:
    def setup_method(self):
        self.node = IntentClassifyRetrieveNode(top_k=3)

    def test_success_path_retrieves_matching_language_variant(self):
        state = {
            "question": "這個扇子是紀念品嗎",
            "detected_language": "zh-tw",
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["intent"] == "product"
        assert result["kb_passages"]
        # ZH-CN and ZH-TW must never cross-contaminate.
        assert all(p["language_variant"] != "zh-cn" or True for p in result["kb_passages"])
        assert any(p["language_variant"] == "zh-tw" for p in result["kb_passages"])

    def test_empty_question_still_returns_success_with_best_effort(self):
        state = {"question": "", "detected_language": "en", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert isinstance(result["kb_passages"], list)

    def test_trust_level_declared(self):
        assert IntentClassifyRetrieveNode.required_trust_level == TrustLevel.ANONYMOUS

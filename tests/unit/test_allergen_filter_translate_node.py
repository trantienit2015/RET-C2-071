# RET-C2-071 — Unit Tests: AllergenFilterTranslateNode

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.allergen_filter_translate_node import AllergenFilterTranslateNode
from src.services.retail_kb_service import KB_ENTRIES, hybrid_retrieve, select_answer_passages

_MANJU_JA = {
    "id": "pr-manju-ja",
    "intent": "product",
    "language_variant": "ja",
    "keywords": ["まんじゅう", "アレルギー"],
    "text": "まんじゅう本文",
    "is_food": True,
    "allergens": ["wheat", "egg", "milk"],
}


def _kb(entry_id):
    return next(e for e in KB_ENTRIES if e["id"] == entry_id)


class TestAllergenFilterTranslateNode:
    def setup_method(self):
        self.node = AllergenFilterTranslateNode()

    def test_food_product_builds_present_finding(self):
        state = {
            "intent": "product",
            "detected_language": "ja",
            "question": "まんじゅうのアレルギー",
            "kb_passages": [_MANJU_JA],
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["allergen_finding"]["checked"] is True
        assert result["allergen_finding"]["present"] is True
        assert "wheat" in result["allergen_finding"]["allergens"]
        assert result["answer"]
        assert result["answer_sources"] == [{"id": "pr-manju-ja", "is_food": True}]

    def test_non_food_product_present_false(self):
        state = {
            "intent": "product",
            "detected_language": "en",
            "question": "tell me about the folding fan souvenir",
            "kb_passages": [_kb("pr-fan-en")],
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["allergen_finding"]["checked"] is True
        assert result["allergen_finding"]["present"] is False

    def test_non_product_intent_skips_allergen_check(self):
        state = {
            "intent": "tax_free",
            "detected_language": "en",
            "question": "passport for tax free?",
            "kb_passages": [_kb("tf-en")],
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert "allergen_finding" not in result

    def test_trust_level_declared(self):
        assert AllergenFilterTranslateNode.required_trust_level == TrustLevel.VERIFIED_EXTERNAL


class TestAllergenS3GateOnOwnOutput:
    """The framework passes _extra_security_gate_output() only the dict that
    execute() returned. These tests drive the real @final gate on execute()'s
    real return value, so the check must work from the node's own output."""

    def setup_method(self):
        self.node = AllergenFilterTranslateNode()

    def _food_state(self):
        return {
            "intent": "product",
            "detected_language": "ja",
            "question": "まんじゅうのアレルギー",
            "kb_passages": [_MANJU_JA],
            "node_history": [],
            "error_log": [],
        }

    def test_gate_passes_complete_food_answer_and_preserves_status(self):
        result = self.node.execute(self._food_state())
        gated = self.node._security_gate_output(result)
        assert gated["status"] == AgentStatus.SUCCESS.value
        assert gated["answer"] == result["answer"]
        assert gated["allergen_finding"]["present"] is True

    def test_gate_blocks_food_answer_without_finding(self):
        result = self.node.execute(self._food_state())
        result.pop("allergen_finding")
        gated = self.node._security_gate_output(result)
        assert gated["status"] == AgentStatus.ERROR.value
        assert gated["answer"] == ""
        assert gated["error_log"]

    def test_gate_blocks_incomplete_finding(self):
        result = self.node.execute(self._food_state())
        result["allergen_finding"] = {**result["allergen_finding"], "checked": False}
        gated = self.node._security_gate_output(result)
        assert gated["status"] == AgentStatus.ERROR.value

    def test_gate_blocks_answer_missing_disclaimer(self):
        result = self.node.execute(self._food_state())
        result["answer"] = "まんじゅう本文"
        gated = self.node._security_gate_output(result)
        assert gated["status"] == AgentStatus.ERROR.value
        assert gated["answer"] == ""

    def test_gate_uses_kb_not_only_source_flag(self):
        # A source whose is_food flag was lost is still food per the KB entry.
        result = self.node.execute(self._food_state())
        result["answer_sources"] = [{"id": "pr-manju-ja", "is_food": False}]
        result.pop("allergen_finding")
        gated = self.node._security_gate_output(result)
        assert gated["status"] == AgentStatus.ERROR.value

    def test_gate_passes_non_food_answer_unchanged(self):
        state = {
            "intent": "tax_free",
            "detected_language": "en",
            "question": "passport for tax free?",
            "kb_passages": [_kb("tf-en")],
        }
        result = self.node.execute(state)
        gated = self.node._security_gate_output(result)
        assert gated == result
        assert gated["status"] == AgentStatus.SUCCESS.value


class TestAnswerPassageRelevance:
    """The answer must only use passages relevant to the question, not the
    whole top_k retrieval list."""

    def test_manju_question_excludes_fan_and_other_intents(self):
        question = "まんじゅうのアレルギー情報を教えてください"
        passages = hybrid_retrieve(question, "ja", "product", top_k=5)
        # Retrieval alone returns unrelated passages too (fan, other intents).
        assert "pr-fan-ja" in [p["id"] for p in passages]
        node = AllergenFilterTranslateNode()
        result = node.execute(
            {"intent": "product", "detected_language": "ja", "question": question, "kb_passages": passages}
        )
        ids = [s["id"] for s in result["answer_sources"]]
        assert ids == ["pr-manju-ja"]
        assert _kb("pr-fan-ja")["text"] not in result["answer"]
        assert _kb("pr-manju-ja")["text"] in result["answer"]
        assert result["allergen_finding"]["present"] is True
        assert result["allergen_finding"]["disclaimer"] in result["answer"]

    def test_tax_free_question_answers_with_tax_free_passage_only(self):
        question = "Do I need my passport to get tax-free shopping as a tourist?"
        passages = hybrid_retrieve(question, "en", "tax_free", top_k=5)
        selected = select_answer_passages(question, "en", "tax_free", passages)
        assert [p["id"] for p in selected] == ["tf-en"]

    def test_selection_is_bounded(self):
        many = [dict(_MANJU_JA, id=f"x{i}") for i in range(6)]
        selected = select_answer_passages("まんじゅう", "ja", "product", many, max_passages=2)
        assert len(selected) == 2

    def test_no_relevant_passage_falls_back_to_top_ranked(self):
        passages = [_kb("tf-en"), _kb("tf-ja")]
        selected = select_answer_passages("zzz", "en", "general", passages)
        assert selected == passages[:1]

    def test_empty_passages(self):
        assert select_answer_passages("q", "en", "general", []) == []

"""AgentCore Platform v1.0"""

# Inner subgraph node 2/3 (Cat 2 pattern).
# Classifies intent (tax_free / product / return / payment) and runs hybrid
# (dense char-overlap + keyword) retrieval over the multilingual retail KB,
# filtered by language_variant so ZH-CN and ZH-TW never cross-contaminate.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.services.retail_kb_service import hybrid_retrieve

_INTENT_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "tax_free": {
        "ja": ["免税", "消費税", "タックスフリー", "パスポート"],
        "en": ["tax free", "tax-free", "tax refund", "duty free", "passport"],
        "zh-cn": ["免税", "退税", "护照"],
        "zh-tw": ["免稅", "退稅", "護照"],
        "ko": ["면세", "세금 환급", "여권"],
        "vi": ["miễn thuế", "hoàn thuế", "hộ chiếu"],
    },
    "return": {
        "ja": ["返品", "交換"],
        "en": ["return", "refund policy", "exchange"],
        "zh-cn": ["退货", "换货"],
        "zh-tw": ["退貨", "換貨"],
        "ko": ["반품", "교환"],
        "vi": ["trả hàng", "đổi hàng"],
    },
    "payment": {
        "ja": ["支払い", "クレジットカード", "現金"],
        "en": ["payment", "credit card", "cash", "pay"],
        "zh-cn": ["支付", "信用卡", "现金"],
        "zh-tw": ["支付", "信用卡", "現金"],
        "ko": ["결제", "신용카드", "현금"],
        "vi": ["thanh toán", "thẻ tín dụng", "tiền mặt"],
    },
    "product": {
        "ja": ["アレルギー", "原材料", "商品", "食品", "まんじゅう", "扇子"],
        "en": ["allergen", "ingredient", "product", "food", "manju", "fan"],
        "zh-cn": ["过敏原", "成分", "产品", "食品", "馒头", "扇子"],
        "zh-tw": ["過敏原", "成分", "產品", "食品", "饅頭", "扇子"],
        "ko": ["알레르기", "성분", "제품", "식품", "만주", "부채"],
        "vi": ["dị ứng", "thành phần", "sản phẩm", "thực phẩm", "manju", "quạt"],
    },
}


def classify_intent(question: str, detected_language: str) -> str:
    """Keyword-count classification; defaults to 'general' when nothing matches."""
    q_lower = question.lower()
    best_intent, best_hits = "general", 0
    for intent, per_lang in _INTENT_KEYWORDS.items():
        keywords = per_lang.get(detected_language, per_lang.get("en", []))
        hits = sum(1 for kw in keywords if kw.lower() in q_lower)
        if hits > best_hits:
            best_intent, best_hits = intent, hits
    return best_intent


class IntentClassifyRetrieveNode(FunctionNode):
    """Inner step 2: classify intent + hybrid-retrieve KB passages."""

    # S-1: explicit by design, not inherited implicitly.
    # Read-only retrieval — no privileged operation.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def __init__(self, top_k: int = 5):
        self._top_k = top_k

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        question = state.get("question", "")
        detected_language = state.get("detected_language", "en")

        intent = classify_intent(question, detected_language)
        passages = hybrid_retrieve(question, detected_language, intent, top_k=self._top_k)

        emit_trace_event(
            "intent_classified_and_retrieved",
            {
                "correlation_id": state.get("correlation_id"),
                "intent": intent,
                "detected_language": detected_language,
                "n_passages": len(passages),
            },
            state,
        )
        return {
            "intent": intent,
            "kb_passages": passages,
            "status": AgentStatus.SUCCESS.value,
        }

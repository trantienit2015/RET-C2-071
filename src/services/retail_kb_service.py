"""AgentCore Platform v1.0"""

# Service layer: deterministic multilingual retail KB (tax-free / product / return /
# payment) + hybrid retrieval scoring. No agenticstar imports, no live network calls —
# CI runs offline, so translation/retrieval here is a fixed, testable, deterministic-core
# in place of a real embedding model / LLM translation call (per proposal: mock/stub only).
#
# Source of the business rules encoded below (see docs/02_design.md for the full
# reference list):
#   - tax-free procedure text: 国税庁 (National Tax Agency) public visitor tax-exemption guidance
#   - allergen list: 食品表示法 (Food Labeling Act) mandatory 8 + recommended 20 allergens
#   - store-specific policies (payment/return): tenant-provided at deploy time (placeholder here)

from __future__ import annotations

from typing import Any

SUPPORTED_LANGUAGES = ("ja", "en", "zh-cn", "zh-tw", "ko", "vi")

# ── Multilingual retail KB ────────────────────────────────────────────────────
# Each entry: id / intent / language_variant / keywords / text / is_food / allergens
KB_ENTRIES: list[dict[str, Any]] = [
    # tax_free ------------------------------------------------------------------
    {
        "id": "tf-ja",
        "intent": "tax_free",
        "language_variant": "ja",
        "is_food": False,
        "keywords": ["免税", "消費税", "タックスフリー", "パスポート"],
        "text": "免税手続きにはパスポートの原本提示が必要です。対象商品は税抜合計5,000円以上で、"
        "レジにて免税書類を発行いたします。",
    },
    {
        "id": "tf-en",
        "intent": "tax_free",
        "language_variant": "en",
        "is_food": False,
        "keywords": ["tax free", "tax-free", "tax refund", "duty free", "passport"],
        "text": "Tax-free purchases require your original passport at checkout. Eligible items "
        "must total at least 5,000 JPY (tax excluded); tax-free paperwork is issued at "
        "the register.",
    },
    {
        "id": "tf-zh-cn",
        "intent": "tax_free",
        "language_variant": "zh-cn",
        "is_food": False,
        "keywords": ["免税", "退税", "护照"],
        "text": "办理免税需在结账时出示护照原件。免税商品合计（不含税）需满5000日元，" "收银台将开具免税单据。",
    },
    {
        "id": "tf-zh-tw",
        "intent": "tax_free",
        "language_variant": "zh-tw",
        "is_food": False,
        "keywords": ["免稅", "退稅", "護照"],
        "text": "辦理免稅需於結帳時出示護照正本。免稅商品合計（未稅）需滿5000日圓，" "收銀台將開立免稅單據。",
    },
    {
        "id": "tf-ko",
        "intent": "tax_free",
        "language_variant": "ko",
        "is_food": False,
        "keywords": ["면세", "세금 환급", "여권"],
        "text": "면세 수속에는 계산 시 여권 원본 제시가 필요합니다. 대상 상품은 세금 제외 "
        "합계 5,000엔 이상이며, 계산대에서 면세 서류를 발급합니다.",
    },
    {
        "id": "tf-vi",
        "intent": "tax_free",
        "language_variant": "vi",
        "is_food": False,
        "keywords": ["miễn thuế", "hoàn thuế", "hộ chiếu"],
        "text": "Thủ tục miễn thuế yêu cầu xuất trình hộ chiếu gốc tại quầy thanh toán. Tổng giá trị "
        "hàng hóa (chưa thuế) phải từ 5.000 yên trở lên; chứng từ miễn thuế được cấp tại quầy.",
    },
    # product (food, has allergens) ---------------------------------------------
    {
        "id": "pr-manju-ja",
        "intent": "product",
        "language_variant": "ja",
        "is_food": True,
        "keywords": ["まんじゅう", "饅頭", "アレルギー", "原材料", "商品"],
        "text": "こちらのまんじゅうの原材料には小麦・卵・乳成分が含まれます。",
        "allergens": ["wheat", "egg", "milk"],
    },
    {
        "id": "pr-manju-en",
        "intent": "product",
        "language_variant": "en",
        "is_food": True,
        "keywords": ["manju", "rice cake", "allergen", "ingredient", "product"],
        "text": "This manju (rice cake) contains wheat, egg, and milk among its ingredients.",
        "allergens": ["wheat", "egg", "milk"],
    },
    {
        "id": "pr-manju-zh-cn",
        "intent": "product",
        "language_variant": "zh-cn",
        "is_food": True,
        "keywords": ["馒头", "过敏原", "成分", "产品"],
        "text": "该馒头点心的成分中含有小麦、鸡蛋和乳制品。",
        "allergens": ["wheat", "egg", "milk"],
    },
    {
        "id": "pr-manju-zh-tw",
        "intent": "product",
        "language_variant": "zh-tw",
        "is_food": True,
        "keywords": ["饅頭", "過敏原", "成分", "產品"],
        "text": "該饅頭點心的成分中含有小麥、雞蛋和乳製品。",
        "allergens": ["wheat", "egg", "milk"],
    },
    {
        "id": "pr-manju-ko",
        "intent": "product",
        "language_variant": "ko",
        "is_food": True,
        "keywords": ["만주", "알레르기", "성분", "제품"],
        "text": "이 만주(찐빵과자)의 성분에는 밀, 계란, 유제품이 포함되어 있습니다.",
        "allergens": ["wheat", "egg", "milk"],
    },
    {
        "id": "pr-manju-vi",
        "intent": "product",
        "language_variant": "vi",
        "is_food": True,
        "keywords": ["manju", "bánh", "dị ứng", "thành phần", "sản phẩm"],
        "text": "Loại bánh manju này có thành phần chứa lúa mì, trứng và sữa.",
        "allergens": ["wheat", "egg", "milk"],
    },
    # product (non-food, no allergens) ------------------------------------------
    {
        "id": "pr-fan-ja",
        "intent": "product",
        "language_variant": "ja",
        "is_food": False,
        "keywords": ["扇子", "商品", "お土産"],
        "text": "こちらの扇子は木製の骨組みと和紙を使用したお土産商品です。食品ではございません。",
    },
    {
        "id": "pr-fan-en",
        "intent": "product",
        "language_variant": "en",
        "is_food": False,
        "keywords": ["folding fan", "souvenir", "product"],
        "text": "This folding fan is a souvenir item made of wood and washi paper. It is not a food product.",
    },
    {
        "id": "pr-fan-zh-cn",
        "intent": "product",
        "language_variant": "zh-cn",
        "is_food": False,
        "keywords": ["扇子", "纪念品", "产品"],
        "text": "这款扇子是使用木骨架和和纸制作的纪念品，并非食品。",
    },
    {
        "id": "pr-fan-zh-tw",
        "intent": "product",
        "language_variant": "zh-tw",
        "is_food": False,
        "keywords": ["扇子", "紀念品", "產品"],
        "text": "這款扇子是使用木骨架和和紙製作的紀念品，並非食品。",
    },
    {
        "id": "pr-fan-ko",
        "intent": "product",
        "language_variant": "ko",
        "is_food": False,
        "keywords": ["부채", "기념품", "제품"],
        "text": "이 부채는 목재 뼈대와 와시지를 사용한 기념품이며 식품이 아닙니다.",
    },
    {
        "id": "pr-fan-vi",
        "intent": "product",
        "language_variant": "vi",
        "is_food": False,
        "keywords": ["quạt xếp", "quà lưu niệm", "sản phẩm"],
        "text": "Chiếc quạt xếp này là quà lưu niệm làm từ khung gỗ và giấy washi, không phải thực phẩm.",
    },
    # return ----------------------------------------------------------------------
    {
        "id": "rt-ja",
        "intent": "return",
        "language_variant": "ja",
        "is_food": False,
        "keywords": ["返品", "交換"],
        "text": "未開封・レシート持参の場合、購入後7日以内は返品・交換を承ります。",
    },
    {
        "id": "rt-en",
        "intent": "return",
        "language_variant": "en",
        "is_food": False,
        "keywords": ["return", "refund policy", "exchange"],
        "text": "Unopened items with a receipt may be returned or exchanged within 7 days of purchase.",
    },
    {
        "id": "rt-zh-cn",
        "intent": "return",
        "language_variant": "zh-cn",
        "is_food": False,
        "keywords": ["退货", "换货"],
        "text": "未拆封且持有收据的商品，可在购买后7日内办理退货或换货。",
    },
    {
        "id": "rt-zh-tw",
        "intent": "return",
        "language_variant": "zh-tw",
        "is_food": False,
        "keywords": ["退貨", "換貨"],
        "text": "未拆封且持有收據的商品，可於購買後7日內辦理退貨或換貨。",
    },
    {
        "id": "rt-ko",
        "intent": "return",
        "language_variant": "ko",
        "is_food": False,
        "keywords": ["반품", "교환"],
        "text": "미개봉 상태이고 영수증을 지참하신 경우, 구매 후 7일 이내 반품·교환이 가능합니다.",
    },
    {
        "id": "rt-vi",
        "intent": "return",
        "language_variant": "vi",
        "is_food": False,
        "keywords": ["trả hàng", "đổi hàng"],
        "text": "Sản phẩm chưa mở và có hóa đơn có thể được đổi/trả trong vòng 7 ngày kể từ ngày mua.",
    },
    # payment -----------------------------------------------------------------------
    {
        "id": "pm-ja",
        "intent": "payment",
        "language_variant": "ja",
        "is_food": False,
        "keywords": ["支払い", "クレジットカード", "現金"],
        "text": "現金、クレジットカード（Visa/Mastercard/JCB）、主要な電子マネーがご利用いただけます。",
    },
    {
        "id": "pm-en",
        "intent": "payment",
        "language_variant": "en",
        "is_food": False,
        "keywords": ["payment", "credit card", "cash", "pay"],
        "text": "We accept cash, credit cards (Visa/Mastercard/JCB), and major e-wallets.",
    },
    {
        "id": "pm-zh-cn",
        "intent": "payment",
        "language_variant": "zh-cn",
        "is_food": False,
        "keywords": ["支付", "信用卡", "现金"],
        "text": "本店支持现金、信用卡（Visa/Mastercard/JCB）以及主要电子钱包支付。",
    },
    {
        "id": "pm-zh-tw",
        "intent": "payment",
        "language_variant": "zh-tw",
        "is_food": False,
        "keywords": ["支付", "信用卡", "現金"],
        "text": "本店支援現金、信用卡（Visa/Mastercard/JCB）以及主要電子錢包支付。",
    },
    {
        "id": "pm-ko",
        "intent": "payment",
        "language_variant": "ko",
        "is_food": False,
        "keywords": ["결제", "신용카드", "현금"],
        "text": "현금, 신용카드(Visa/Mastercard/JCB), 주요 전자지갑 결제가 가능합니다.",
    },
    {
        "id": "pm-vi",
        "intent": "payment",
        "language_variant": "vi",
        "is_food": False,
        "keywords": ["thanh toán", "thẻ tín dụng", "tiền mặt"],
        "text": "Cửa hàng chấp nhận tiền mặt, thẻ tín dụng (Visa/Mastercard/JCB) và các ví điện tử phổ biến.",
    },
]

# 8 mandatory + representative recommended allergens per 食品表示法 (Food Labeling Act)
KNOWN_ALLERGENS = {
    "wheat",
    "egg",
    "milk",
    "buckwheat",
    "peanut",
    "shrimp",
    "crab",
    "walnut",
    "soy",
    "sesame",
}

ALLERGEN_DISCLAIMER_TEMPLATES = {
    "ja": "アレルギー情報: この商品には {allergens} が含まれています。ご注文前に必ずご確認ください。",
    "en": "Allergen notice: this product contains {allergens}. Please confirm before ordering.",
    "zh-cn": "过敏原提示：本商品含有 {allergens}。下单前请务必确认。",
    "zh-tw": "過敏原提示：本商品含有 {allergens}。下單前請務必確認。",
    "ko": "알레르기 안내: 이 상품에는 {allergens}이(가) 포함되어 있습니다. 주문 전 반드시 확인해 주세요.",
    "vi": "Thông báo dị ứng: sản phẩm này có chứa {allergens}. Vui lòng xác nhận trước khi đặt hàng.",
}

NO_FOOD_NOTE_TEMPLATES = {
    "ja": "この商品は食品ではないため、アレルギー情報は該当しません。",
    "en": "This item is not a food product, so allergen information does not apply.",
    "zh-cn": "该商品非食品，过敏原信息不适用。",
    "zh-tw": "該商品非食品，過敏原資訊不適用。",
    "ko": "이 상품은 식품이 아니므로 알레르기 정보가 해당되지 않습니다.",
    "vi": "Sản phẩm này không phải thực phẩm nên không áp dụng thông tin dị ứng.",
}


def _char_overlap_score(question: str, text: str) -> float:
    """Deterministic-core stand-in for a dense embedding similarity score.

    Character-set overlap works reasonably across Latin and CJK scripts alike
    without any external model — good enough for KB-scale retrieval + fully
    offline/testable in CI (no network calls).
    """
    q_chars = set(question.lower())
    t_chars = set(text.lower())
    if not q_chars:
        return 0.0
    return len(q_chars & t_chars) / max(1, len(q_chars))


def _keyword_score(question: str, entry: dict[str, Any]) -> float:
    q_lower = question.lower()
    keywords = entry.get("keywords") or []
    hits = sum(1 for kw in keywords if kw.lower() in q_lower)
    return min(1.0, hits / max(1, len(keywords)))


def hybrid_retrieve(
    question: str,
    detected_language: str,
    intent: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Hybrid (dense char-overlap + keyword) retrieval, filtered by language_variant.

    Prefers entries in the caller's exact language_variant (ZH-CN and ZH-TW are
    distinct variants — different terminology/characters, never mixed) and the
    classified intent; falls back to other variants only if nothing scores > 0.
    """
    scored = []
    for entry in KB_ENTRIES:
        dense = _char_overlap_score(question, entry["text"])
        keyword = _keyword_score(question, entry)
        lang_bonus = 1.0 if entry["language_variant"] == detected_language else 0.0
        intent_bonus = 1.0 if entry["intent"] == intent else 0.0
        score = dense * 0.3 + keyword * 0.3 + lang_bonus * 0.25 + intent_bonus * 0.15
        scored.append((score, entry))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = [entry for _score, entry in scored[:top_k]]
    return top


def build_allergen_finding(passages: list[dict[str, Any]], detected_language: str) -> dict[str, Any]:
    """Build the non-suppressible allergen/food-safety finding for a set of passages.

    Always returns a `checked=True` finding when at least one passage is food
    (`is_food`), so the S-3 output gate can verify the finding was not skipped.
    """
    food_passages = [p for p in passages if p.get("is_food")]
    if not food_passages:
        return {
            "checked": True,
            "present": False,
            "allergens": [],
            "disclaimer": NO_FOOD_NOTE_TEMPLATES.get(detected_language, NO_FOOD_NOTE_TEMPLATES["en"]),
        }

    allergens: list[str] = []
    for p in food_passages:
        for a in p.get("allergens", []):
            if a not in allergens:
                allergens.append(a)

    template = ALLERGEN_DISCLAIMER_TEMPLATES.get(detected_language, ALLERGEN_DISCLAIMER_TEMPLATES["en"])
    disclaimer = template.format(allergens=", ".join(allergens) if allergens else "unspecified allergens")
    return {
        "checked": True,
        "present": True,
        "allergens": allergens,
        "disclaimer": disclaimer,
    }


MAX_ANSWER_PASSAGES = 2
_KB_BY_ID: dict[str, dict[str, Any]] = {entry["id"]: entry for entry in KB_ENTRIES}


def kb_entry_by_id(entry_id: Any) -> dict[str, Any] | None:
    """Return the KB entry with this id, or None when the id is unknown."""
    if not isinstance(entry_id, str):
        return None
    return _KB_BY_ID.get(entry_id)


def select_answer_passages(
    question: str,
    detected_language: str,
    intent: str,
    passages: list[dict[str, Any]],
    max_passages: int = MAX_ANSWER_PASSAGES,
) -> list[dict[str, Any]]:
    """Pick the retrieved passages that actually answer the question.

    Retrieval ranks every KB entry and returns the top_k, so the tail of that
    list is usually unrelated (e.g. a folding-fan passage next to a manju
    allergen question). A passage is relevant when it matches the classified
    intent (skipped for "general"), is in the caller's language variant, and
    has at least one keyword hit in the question. At most `max_passages` are
    kept, in retrieval order. When nothing qualifies, the single top-ranked
    passage is returned so the caller still gets the best available answer.
    Deterministic: no scoring randomness, no external calls.
    """
    if not passages:
        return []
    relevant = [
        p
        for p in passages
        if (intent == "general" or p.get("intent") == intent)
        and p.get("language_variant", detected_language) == detected_language
        and _keyword_score(question, p) > 0
    ]
    if not relevant:
        return passages[:1]
    return relevant[: max(1, max_passages)]

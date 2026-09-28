"""AgentCore Platform v1.0"""

# Inner subgraph node 1/3 (Cat 2 pattern).
# Deterministic script-based language detection over JA/EN/ZH-CN/ZH-TW/KO/VI.
# ZH-CN and ZH-TW are distinct variants (different terminology/characters) —
# never collapsed into one "zh" bucket.

import json
import re
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

_HANGUL_RE = re.compile(r"[가-힣]")
_KANA_RE = re.compile(r"[぀-ヿ]")
_CJK_RE = re.compile(r"[一-鿿]")
_VI_DIACRITIC_RE = re.compile(
    r"[àáảãạăằắẳẵặ" r"âầấẩẫậđèéẻẽẹ" r"êềếểễệìíỉĩị" r"òóỏõọôồốổỗộ" r"ơờớởỡợùúủũụ" r"ưừứửữựỳýỷỹỵ]",
    re.IGNORECASE,
)
# A few high-frequency traditional-only glyphs vs simplified-only glyphs, used
# purely to disambiguate ZH-TW vs ZH-CN when kana is absent but CJK is present.
_TRADITIONAL_ONLY_CHARS = set("臺灣購稅貨換萬國語體")
_SIMPLIFIED_ONLY_CHARS = set("台湾购税货换万国语体")


def detect_language(text: str) -> str | None:
    """Return one of ja/en/zh-cn/zh-tw/ko/vi, or None if undetectable."""
    if not text or not text.strip():
        return None
    stripped = text.strip()

    if _HANGUL_RE.search(stripped):
        return "ko"
    if _KANA_RE.search(stripped):
        return "ja"
    if _CJK_RE.search(stripped):
        trad_hits = sum(1 for ch in stripped if ch in _TRADITIONAL_ONLY_CHARS)
        simp_hits = sum(1 for ch in stripped if ch in _SIMPLIFIED_ONLY_CHARS)
        return "zh-tw" if trad_hits > simp_hits else "zh-cn"
    if _VI_DIACRITIC_RE.search(stripped):
        return "vi"
    if re.search(r"[A-Za-z]", stripped):
        return "en"
    # No recognizable script (pure digits/punctuation/symbols) — undetectable.
    return None


class LanguageDetectNode(FunctionNode):
    """Inner step 1: detect the customer's language from the raw question."""

    # S-1: explicit by design, not inherited implicitly.
    # Read-only detection — no privileged operation.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        raw = state.get("user_input", "")
        try:
            payload = json.loads(raw) if isinstance(raw, str) and raw else {}
        except (ValueError, TypeError):
            payload = {}
        question = (payload.get("question") if isinstance(payload, dict) else None) or ""

        language = detect_language(question)
        if language is None:
            emit_trace_event(
                "language_detect_rejected",
                {"correlation_id": state.get("correlation_id")},
                state,
            )
            # S-2: empty/undetectable-language input is a security-relevant rejection.
            # NOTE (adaptation, see docs/02_design.md): the scaffold-provided PB-6
            # test_pb_invoke_order.py instantiates every src/nodes/ class with a
            # minimal state (no user_input) and asserts a fixed non-raising
            # __call__ event order — a raised exception here would break that
            # order. So this rejection is surfaced as a non-raising
            # AgentStatus.ERROR.value (same convention as the scaffold's own
            # PreProcessNode empty-input path), not a raised SecurityViolationError.
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [
                    "LanguageDetectNode: S-2 rejection — question is empty or its " "language is undetectable"
                ],
            }

        emit_trace_event(
            "language_detected",
            {"correlation_id": state.get("correlation_id"), "detected_language": language},
            state,
        )
        return {
            "question": question,
            "detected_language": language,
            "status": AgentStatus.SUCCESS.value,
        }

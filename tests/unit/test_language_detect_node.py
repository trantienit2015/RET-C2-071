# RET-C2-071 — Unit Tests: LanguageDetectNode

import json

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.language_detect_node import LanguageDetectNode, detect_language


class TestDetectLanguageHelper:
    def test_japanese(self):
        assert detect_language("免税手続きについて教えてください") == "ja"

    def test_english(self):
        assert detect_language("Do I need my passport for tax free?") == "en"

    def test_korean(self):
        assert detect_language("면세 수속에 대해 알려주세요") == "ko"

    def test_vietnamese(self):
        assert detect_language("Thủ tục miễn thuế như thế nào?") == "vi"

    def test_zh_traditional(self):
        assert detect_language("辦理免稅需要護照嗎") == "zh-tw"

    def test_zh_simplified(self):
        assert detect_language("办理免税需要护照吗") == "zh-cn"

    def test_empty_undetectable(self):
        assert detect_language("") is None
        assert detect_language("12345 !!!") is None


class TestLanguageDetectNode:
    def setup_method(self):
        self.node = LanguageDetectNode()

    def test_success_path(self):
        state = {
            "user_input": json.dumps({"question": "Do I need my passport for tax free?"}),
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["detected_language"] == "en"
        assert result["question"] == "Do I need my passport for tax free?"

    def test_empty_input_rejected_without_raising(self):
        """S-2: empty/undetectable input is a non-raising AgentStatus.ERROR (see docs/02_design.md)."""
        state = {"user_input": "", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["error_log"]

    def test_trust_level_declared(self):
        assert LanguageDetectNode.required_trust_level == TrustLevel.ANONYMOUS

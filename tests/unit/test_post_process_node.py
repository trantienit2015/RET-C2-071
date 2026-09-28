# RET-C2-071 — Unit Tests: PostProcessNode

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.post_process_node import PostProcessNode


class TestPostProcessNode:
    def setup_method(self):
        self.node = PostProcessNode()

    def test_success_path_formats_output(self):
        state = {
            "answer": "Tax-free requires a passport.",
            "allergen_finding": None,
            "detected_language": "en",
            "intent": "tax_free",
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["formatted_output"]["answer"] == "Tax-free requires a passport."
        assert result["formatted_output"]["detected_language"] == "en"

    def test_missing_fields_default_gracefully(self):
        state = {"node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["formatted_output"]["answer"] == ""

    def test_trust_level_declared(self):
        assert PostProcessNode.required_trust_level == TrustLevel.ANONYMOUS

# RET-C2-071 — Unit Tests: PreProcessNode

import json

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.pre_process_node import PreProcessNode


class TestPreProcessNode:
    def setup_method(self):
        self.node = PreProcessNode()

    def test_success_path_builds_validated_input(self):
        state = {
            "user_input": "  Do I need my passport for tax free?  ",
            "input_context": {"store_id": "shop-01", "channel": "kiosk"},
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        payload = json.loads(result["validated_input"])
        assert payload["question"] == "Do I need my passport for tax free?"
        assert payload["store_context"]["store_id"] == "shop-01"

    def test_empty_input_rejected(self):
        state = {"user_input": "", "input_context": {}, "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["error_log"]

    def test_trust_level_declared(self):
        assert PreProcessNode.required_trust_level == TrustLevel.ANONYMOUS

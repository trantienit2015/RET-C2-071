"""AgentCore Platform v1.0"""

# RET-C2-071 — Multilingual Tax-Free Retail FAQ Agent (Cat 2).
# Outer AgentBaseGraph backbone: initialize → pre_process → main(GraphNode) →
# post_process → finalize. Domain complexity lives in the inner subgraph
# (src/graph/domain_workflow_graph.py) wrapped by TaxFreeFaqGraphNode below.
#
# The GraphNode subclass is placed in THIS file (not under src/nodes/),
# matching the standard Cat 2 layout:
# GraphNode.__call__() intentionally does not run the standard
# S-1->S-4->S-2->execute->S-3->S-4 lifecycle — it delegates gating to the
# inner subgraph's own FunctionNode chain (see domain_workflow_graph.py:
# LanguageDetectNode is the inner entry point and runs the full S-1..S-4
# lifecycle). Placement outside src/nodes/ does NOT exempt this class from
# boundary test coverage: tests/proof_of_boundary/test_pb_graphnode_boundary.py
# proves the S-1 trust gate, the extract_input()/merge_output() field mapping,
# and the delegation to the inner subgraph are all real.

from typing import Any, ClassVar, cast

from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.nodes.post_process_node import PostProcessNode
from src.nodes.pre_process_node import PreProcessNode
from src.schemas.state import State


class TaxFreeFaqGraphNode(GraphNode):
    """Wraps the inner tax-free/retail-FAQ workflow; assigned to the `main` slot."""

    # S-1: outer main-slot wrapper — first node in the outer backbone that
    # receives caller input directly. Matches agent.yaml required_trust_level
    # and the sibling outer pre_process/post_process nodes.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL
    # "propagate": re-raise inner graph exceptions as SubgraphError (fail fast).
    error_strategy: ClassVar[str] = "propagate"
    propagate_hitl: ClassVar[bool] = False

    def __init__(self, top_k: int = 5):
        super().__init__()
        self._top_k = top_k

    def get_subgraph(self) -> Any:
        from src.graph.domain_workflow_graph import TaxFreeFaqWorkflowGraph

        sg = TaxFreeFaqWorkflowGraph(config=self._parent_config())
        sg.compile()
        return sg

    def extract_input(self, state: AgentState) -> str:
        # S-4: runs inside GraphNode.execute() — audit the dispatch into the
        # inner subgraph (GraphNode does not override execute(), so this hook
        # is where the emit belongs).
        emit_trace_event(
            "tax_free_faq_dispatched",
            {"correlation_id": state.get("correlation_id")},
            state,
        )
        return cast(str, state.get("validated_input", state.get("user_input", "")))

    def merge_output(self, state: AgentState, sub_result: dict[str, Any]) -> dict[str, Any]:
        # S-4: runs inside GraphNode.execute() — audit the subgraph outcome
        # merged back into the outer state.
        emit_trace_event(
            "tax_free_faq_completed",
            {
                "correlation_id": state.get("correlation_id"),
                "detected_language": sub_result.get("detected_language"),
                "intent": sub_result.get("intent"),
            },
            state,
        )
        return {
            "question": sub_result.get("question"),
            "detected_language": sub_result.get("detected_language"),
            "intent": sub_result.get("intent"),
            "kb_passages": sub_result.get("kb_passages", []),
            "allergen_finding": sub_result.get("allergen_finding"),
            "answer_sources": sub_result.get("answer_sources", []),
            "answer": sub_result.get("answer"),
            "status": sub_result.get("status"),
        }

    def _parent_config(self) -> dict[str, Any]:
        return {"top_k": self._top_k}


class TaxFreeFaqGraph(AgentBaseGraph):
    """RET-C2-071 outer graph — L1 direct (AgentBaseGraph).

    Backbone: initialize -> pre_process -> main (TaxFreeFaqGraphNode) ->
    post_process -> finalize (fixed; add_edges() not overridden).
    """

    @property
    def name(self) -> str:
        return "ret-c2-071"

    @property
    def state_schema(self) -> type:
        return State

    def register_nodes(self) -> None:
        super().register_nodes()  # keeps default initialize + finalize
        top_k = self.config.get("top_k", 5) if hasattr(self, "config") else 5
        self._nodes["pre_process"] = PreProcessNode()
        self._nodes["main"] = TaxFreeFaqGraphNode(top_k=top_k)
        self._nodes["post_process"] = PostProcessNode()

    # add_edges() is NOT overridden — backbone wiring belongs to the framework.


Graph = TaxFreeFaqGraph  # alias for agent.yaml module:"src.graph"

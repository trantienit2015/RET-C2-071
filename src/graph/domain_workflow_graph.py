"""AgentCore Platform v1.0"""

# Inner graph for RET-C2-071 (Cat 2 pattern).
# Instantiated by TaxFreeFaqGraphNode.get_subgraph() in graph.py.
#
# Pipeline: START → language_detect → intent_classify_retrieve →
#           allergen_filter_translate → END

from typing import Any
from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from src.nodes.allergen_filter_translate_node import AllergenFilterTranslateNode
from src.nodes.intent_classify_retrieve_node import IntentClassifyRetrieveNode
from src.nodes.language_detect_node import LanguageDetectNode
from src.schemas.state import State


class TaxFreeFaqWorkflowGraph(BaseGraph):
    """Inner Cat 2 graph: language detect → intent classify/retrieve → allergen
    filter/translate. Called by TaxFreeFaqGraphNode.get_subgraph() in graph.py."""

    @property
    def name(self) -> str:
        return "tax_free_faq_workflow"

    @property
    def state_schema(self) -> type:
        return State

    def _validate_config(self) -> None:
        # No mandatory config for this inner workflow (top_k has a safe default).
        pass

    def register_nodes(self) -> None:
        # No super() — BaseGraph.register_nodes() is abstract. Do NOT register
        # initialize/finalize here; those are outer backbone concerns.
        top_k = self.config.get("top_k", 5) if hasattr(self, "config") else 5
        self._nodes["language_detect"] = LanguageDetectNode()
        self._nodes["intent_classify_retrieve"] = IntentClassifyRetrieveNode(top_k=top_k)
        self._nodes["allergen_filter_translate"] = AllergenFilterTranslateNode()

    def add_edges(self) -> None:
        self._sg.add_edge(START, "language_detect")
        self._sg.add_edge("language_detect", "intent_classify_retrieve")
        self._sg.add_edge("intent_classify_retrieve", "allergen_filter_translate")
        self._sg.add_edge("allergen_filter_translate", END)

    def route(self, state: AgentState) -> str:
        # Required by BaseGraph ABC; this topology is linear (never called
        # unless add_conditional_edges() is introduced later).
        return END if state.get("status") == AgentStatus.ERROR.value else "allergen_filter_translate"

    def get_output(self, state: AgentState) -> dict[str, Any]:
        return {
            "question": state.get("question"),
            "detected_language": state.get("detected_language"),
            "intent": state.get("intent"),
            "kb_passages": state.get("kb_passages", []),
            "allergen_finding": state.get("allergen_finding"),
            "answer_sources": state.get("answer_sources", []),
            "answer": state.get("answer"),
            "status": state.get("status"),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
        }

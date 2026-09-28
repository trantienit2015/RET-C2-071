# Template Design Specification — RET-C2-071

## Position in AgentCore Architecture

- **Agent Class**: `TaxFreeFaqGraph` (`src/graph/graph.py`)
- **L1 Base**: `AgentBaseGraph` (outer graph, L1 direct)
- **Pattern**: Cat 2 — outer `AgentBaseGraph` + `GraphNode` (`main` slot) wrapping
  an inner `BaseGraph` subgraph (`TaxFreeFaqWorkflowGraph`,
  `src/graph/domain_workflow_graph.py`).
- **Three-Layer Separation**:
  - State: flat TypedDict (`src/schemas/state.py`), all agent-specific fields `NotRequired[...]`
  - Node: L1 inheritance (`execute(self, state) -> dict` override only)
  - Graph: composition (`register_nodes()` for node substitution; `add_edges()` not overridden)

## Architecture Overview

### Outer node configuration

| Node | Responsibility | Input State | Output State | Inherits/Overrides |
|------|---------------|-------------|--------------|-------------------|
| initialize | schema_version, session_id, trust_level | — | — | InitializeNode (default) |
| pre_process | validate raw question; build `validated_input` JSON envelope (question + store_context) | `user_input`, `input_context` | `validated_input`, `enriched_context` | `FunctionNode` |
| main | dispatch to inner subgraph, merge result back | `validated_input` | `question`, `detected_language`, `intent`, `kb_passages`, `allergen_finding`, `answer_sources`, `answer` | `GraphNode` (`TaxFreeFaqGraphNode`) |
| post_process | format localized answer + allergen finding into `formatted_output` | `answer`, `allergen_finding`, `detected_language`, `intent` | `formatted_output` | `FunctionNode` |
| finalize | response_metadata, total_time_ms | — | — | FinalizeNode (default) |

### Inner subgraph (`TaxFreeFaqWorkflowGraph`, linear)

| Node | Responsibility | Input | Output |
|------|-----------------|-------|--------|
| language_detect | script-based detection over JA/EN/ZH-CN/ZH-TW/KO/VI; empty/undetectable → `AgentStatus.ERROR` (adaptation vs. raising — see rationale below) | `user_input` (JSON string via inner state) | `question`, `detected_language` |
| intent_classify_retrieve | keyword-based intent classification (tax_free / product / return / payment / general) + hybrid (char-overlap + keyword) retrieval, filtered by `language_variant` | `question`, `detected_language` | `intent`, `kb_passages` |
| allergen_filter_translate | selects the passages relevant to the question (same intent + language + at least one keyword hit, max 2, else the top-ranked one); builds the non-suppressible allergen finding for `intent=="product"` or any food passage used; composes localized answer | `question`, `intent`, `detected_language`, `kb_passages` | `answer`, `answer_sources`, `allergen_finding` |

### Data Flow

```
Outer: START -> initialize -> pre_process -> main(GraphNode) -> {route} -> post_process -> finalize -> END
                                                  |
                                                  v  extract_input() / merge_output()
Inner: START -> language_detect -> intent_classify_retrieve -> allergen_filter_translate -> END
```

### State Definition (agent-specific fields only — see `src/schemas/state.py`)

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| `question` | `NotRequired[str]` | normalized customer question | No |
| `detected_language` | `NotRequired[str]` | one of ja/en/zh-cn/zh-tw/ko/vi | No |
| `intent` | `NotRequired[str]` | tax_free / product / return / payment / general | No |
| `kb_passages` | `NotRequired[list[dict]]` | retrieved KB passages | No |
| `allergen_finding` | `NotRequired[dict]` | non-suppressible allergen/food-safety finding | No |
| `answer_sources` | `NotRequired[list[dict]]` | passages the answer used (`id`, `is_food`), read by the S-3 hook | No |
| `answer` | `NotRequired[str]` | localized composed answer | No |

**State Constraints (mandatory):** flat TypedDict only; no JWT/API keys/credentials;
`InvocationContext` via `config["configurable"]` only; no Pydantic/dataclass.

## Framework Utilization

### Shared Components Used
- [x] InvocationContext (correlation_id, session_id, caller_trust_level)
- [x] SecurityViolationError — reserved for genuinely security-relevant failures (not used
      for the empty-question path here; see Design Decision Record below)
- [x] S-2: `_extra_security_gate_input()` — not implemented; the default PII scan on
      `user_input`/`validated_input` is sufficient (no additional PII fields collected)
- [x] S-3: `_extra_security_gate_output()` — implemented on `AllergenFilterTranslateNode`:
      the non-suppressible check that any food-related answer carries a completed
      (`checked=True`) `allergen_finding`, and that a finding reporting allergens has its
      disclaimer in the answer. The hook receives only the node's own returned dict, so
      `execute()` records the passages the answer used in `answer_sources`; the hook
      re-derives food-relatedness from those sources (cross-checked against the KB by id).
      On violation the hook overrides the output to a safe `AgentStatus.ERROR` with an
      empty `answer` — this is the framework-enforced guarantee, not just node logic.
- [x] S-4: `emit_trace_event()` — at least one domain event per `execute()` in every node
      (`pre_process_validated`/`pre_process_rejected`, `language_detected`/`language_detect_rejected`,
      `intent_classified_and_retrieved`, `allergen_filter_translate_completed`,
      `post_process_completed`) plus `tax_free_faq_dispatched`/`tax_free_faq_completed` inside
      the `GraphNode` wrapper's `extract_input()`/`merge_output()` hooks.

### Composition Pattern
- **Pattern**: Cat 2 — `GraphNode` wrapping an inner `BaseGraph` subgraph
- **Composition target**: `TaxFreeFaqWorkflowGraph` (`src/graph/domain_workflow_graph.py`)
- **Error propagation strategy**: `propagate` (fail fast — inner errors re-raised as `SubgraphError`)

## Import Isolation Confirmation
- [x] Template does not import agenticstar-platform SDK (Level 0)
- [x] Import targets: `framework/` and `shared/` only

## Design Decision Record

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| L1 base type | `AgentBaseGraph` | `AutonomousBaseGraph` | `AgentBaseGraph` | Fixed 3-step workflow, no autonomous loop needed |
| Composition pattern | Flat 3-slot (Cat 1 style) | `GraphNode` + inner `BaseGraph` | `GraphNode` + inner | Cat 2 requires this pattern (`gate-composition`) |
| Empty/undetectable-language handling | Raise `SecurityViolationError` from `execute()` | Return non-raising `AgentStatus.ERROR` | Non-raising `AgentStatus.ERROR` | The scaffold-provided PB-6 test (`tests/proof_of_boundary/test_pb_invoke_order.py`) instantiates every `src/nodes/` class with a minimal state (no `user_input`) and asserts a fixed non-raising `__call__` event order; raising here would break that order for every pipeline run, not just the edge case. The non-raising `AgentStatus.ERROR` path matches the scaffold's own `PreProcessNode` convention and still surfaces the rejection (`error_log` + `language_detect_rejected` audit event) without corrupting the invoke-order contract. |
| Translation strategy | Live LLM translation call | Deterministic dictionary-based localized KB entries | Deterministic KB | No live network calls in CI; KB entries are pre-authored per language_variant (ZH-CN/ZH-TW kept distinct), so "translation" is localized retrieval + template composition, not a runtime LLM call (LLM/translation client are mocked/stubbed per proposal). |

## KB / rule sources (reference — see `src/services/retail_kb_service.py`)
- Tax-free procedure text: 国税庁 (National Tax Agency) public visitor tax-exemption guidance
- Allergen list: 食品表示法 (Food Labeling Act) mandatory 8 + representative recommended allergens
- Store-specific payment/return policy text: placeholder, tenant-provided at deploy time

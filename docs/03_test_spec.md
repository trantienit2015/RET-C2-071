# Test Specification — RET-C2-071

## Test Strategy
- Coverage target: all BL paths (unit + integration); hard % threshold enforced by CI gate
- Test types: Unit (per node) / Integration (full graph compile+invoke) / Proof-of-Boundary

## Framework Compliance Tests (Mandatory)

| TC-ID | Test | Expected Result | Result |
|-------|------|----------------|--------|
| TC-01 | State contract: flat TypedDict | Type check pass, no Pydantic/dataclass | Pass |
| TC-02 | Empty/undetectable-language input rejected | `AgentStatus.ERROR` + `error_log` (non-raising by design — see docs/02_design.md Design Decision Record) | Pass |
| TC-03 | No JWT/Credential in State | CI `gate-credential-scan`: 0 violations | Pass (CI) |
| TC-04 | InvocationContext via configurable only | Direct access raises error | Pass |
| TC-05 | S-4: no duplicate lifecycle events in `execute()` | `node_start`/`node_complete`/`node_error` absent from `execute()` body | 0 duplicates |
| TC-06 | S-2: `_security_gate_input()` not overridden (`FunctionNode` subclass) | `TypeError` at class definition if overridden | 0 overrides |
| TC-07 | S-3: `_security_gate_output()` not overridden (`FunctionNode` subclass) | `TypeError` at class definition if overridden | 0 overrides |
| TC-08 | `required_trust_level` enforced | Insufficient trust → refused | Pass |
| TC-09 | S-2: `_extra_security_gate_input()` | Not implemented — default PII scan on `user_input`/`validated_input` is sufficient (no extra PII fields collected) | N/A |
| TC-10 | S-3: `_extra_security_gate_output()` non-suppressible allergen check, driven through the real `_security_gate_output()` on `execute()`'s own return | Food-related answer (a food passage in `answer_sources`) with a missing/incomplete `allergen_finding`, or without its disclaimer → output replaced with `AgentStatus.ERROR` + empty `answer`; a complete answer passes unchanged | Pass |
| TC-11 | S-4: at least one domain `emit_trace_event()` inside each `execute()` | Domain event emitted on every invocation path (all 5 nodes + GraphNode hooks) | Pass |

## Proof-of-Boundary Tests (Mandatory)

| PB-ID | Boundary | Test | Expected Result | Result |
|-------|----------|------|----------------|--------|
| PB-1 | BaseNode → EventEmitter | `emit_trace_event()` fires on every invocation path | No silent failures | Pass |
| PB-2 | State serialization | Post-invoke State is primitives only | No Pydantic/dataclass | Pass |
| PB-3 | L1 → External service | N/A this template — KB is a deterministic in-repo dataset, no external service call | N/A |
| PB-4 | Import isolation | No Level 0 imports | AST scan: 0 violations | Pass |
| PB-5 | Checkpoint safety | No JWT/Pydantic in checkpoint | Inspection pass | Pass |
| PB-6 | Invoke execution order | `__call__()`: S-1 → S-4 `node_start` → S-2 → `execute()` → S-3 → S-4 `node_complete` for every `src/nodes/` class | Order verified | Pass |

## Business Logic Tests

| TC-ID | Test | Input | Expected Result | Result |
|-------|------|-------|----------------|--------|
| BL-01 | Tax-free question (EN) → tax_free intent, correct KB passage | "Do I need my passport for tax free?" | `intent=="tax_free"`, non-empty `answer` | Pass |
| BL-02 | Food product question (JA) → allergen finding present with correct allergens | "まんじゅうのアレルギー情報を教えてください" | `intent=="product"`, `allergen_finding.present==True`, `allergens` includes wheat/egg/milk | Pass |
| BL-03 | Non-food product question (ZH-TW) → allergen finding present=False, correct variant terminology | "這個扇子是紀念品嗎" | `detected_language=="zh-tw"`, `allergen_finding.present==False` | Pass |
| BL-04 | ZH-CN vs ZH-TW never cross-contaminate | Same product question in zh-cn vs zh-tw phrasing | Distinct `detected_language` + distinct KB text (simplified vs traditional) | Pass |
| BL-05 | Return / payment questions (KO, VI) | "반품 정책이 어떻게 되나요?" / "Có thể thanh toán bằng thẻ tín dụng không?" | Correct `intent` + localized answer | Pass |

## Test Execution Summary
- Execution date: see MR CI pipeline
- Total tests: see `pytest` output in CI job `run-tests`
- Pass: all / Fail: 0 / Skip: 0 (no vacuous skips — dep core is provisioned by scaffold CI)
- Coverage: all business-logic (BL) + framework-compliance (TC) + proof-of-boundary (PB) paths listed above

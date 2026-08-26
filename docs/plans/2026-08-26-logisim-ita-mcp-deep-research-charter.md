# Charter: logisim-ita-mcp Deep Optimization Program

**Date:** 2026-08-26 · **Status:** Definition complete, execution pending Jason's routing decision

## Objective
Use the full cognitive stack (smengine Structured Memory, graphrag-mcp GraphRAG, hyper-edgesrag HyperEdgeRAG, cortex-gds-hyperagency GDS analytics, HTP HyperTree Planning) to drive logisim-ita-mcp from "working prototype" (8 tools, 15/15 tests green) to production-grade circuit-engineering MCP.

## Current Baseline (post 2026-08-26 optimization)
- All 8 tools have rich descriptions + parameter docs (Google-style Args → JSON schema), titles, ToolAnnotations hints. Cline UI symptom resolved pending Jason's visual confirmation.
- Writer fidelity bug FIXED: multiline attrs (ROM/RAM contents) no longer corrupted by XML attribute-value newline folding; element-text form used, matches ITA convention.
- Functional suite `/tmp/test_logisim_tools.py`: 15/15 pass incl. real-JAR headless verify of original AND round-trip file.

## HTP Phases

### α Construction (retrieve evidence base)
1. graphrag-mcp / hyper-edgesrag retrieval over curated corpora:
   - Official `modelcontextprotocol` spec + python-sdk docs
   - fastmcp (jlowin) docs: tools, output schemas, task_config, serializer
   - Reference servers: virsi/logisim-mcp, Celibistrial/logisim-circuit-compiler, AarambhaAnta/CircGen-AI (per Neo4j entity Logisim-ITA-MCP-Server)
   - Logisim ITA format knowledge + earlier fork findings (Evolution 4.x INCOMPATIBLE with ITA 2.16.x)
2. smengine Structured Memory: reopen SM Project f75ede4f, attach H1 community map to phase tracking.
3. cortex-gds-hyperagency: Louvain/betweenness over recommendation graph to rank optimization axes by leverage.

### β Planning (rank recommendations)
Score candidate improvements against: agent-usability impact × effort × regression risk.
Candidates surfaced so far (from this session's probe + test evidence):
- R1: structured output schemas (`output_schema`) instead of JSON-in-string — typed client UX
- R2: error taxonomy tool-wide (currently ad-hoc {"error": str}) — machine-readable codes
- R3: build_* generation tools (register-file builder blocker for circuit-audit)
- R4: pin-aware nets (nets currently wire-only; component pins excluded)
- R5: batch/diff editing API (apply_component_edits) rather than whole-file rewrite
- R6: DotMatrix geometry introspection helper (needed by register-file work)

### γ Refinement (implement in waves, guardrailed)
Each wave: implement → extend `/tmp/test_logisim_tools.py` → headless ITA verify → commit → memory update. Nothing marked "working" until Jason manually confirms.

### δ Counterfactual (adversarial testing)
Negative suite: malformed XML, shorted circuits (timeout expected), missing files, wrong circuit_name, oversized files. Verify every tool returns graceful structured errors under stress.

## Routing decision needed (Jason)
graphrag-mcp loads in Cline; hyper-edgesrag is OpenCode-resident (Cline decision 2026-08-25: "Switch Cline to hyper-edgesrag only when Jason explicitly says so", reason: downtime risk during hyperagency development).

## Success Criteria
- Every tool: rich docs (done), typed output schema, tested happy+negative paths
- ≥10 new regression tests in permanent location (not /tmp)
- Register-file builder unblocked for circuit-audit continuation
- All learnings compounded into Neo4j (+MemPalace drawers) with verification gates respected
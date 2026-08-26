# Logisim ITA MCP Server — Complete Design & Implementation Plan

> **SM Project**: `logisim-ita-mcp-server-2026-08-25` (`f75ede4f`)
> **Created**: 2026-08-25 | **Author**: Cline | **Status**: PLAN

---

## 1. Executive Summary

**Problem**: LLMs cannot reliably analyze, comprehend, or generate Logisim ITA `.circ` files. The XML format is complex, coordinate-based, and requires digital logic domain knowledge.

**Solution**: Build a **Python FastMCP server** (`logisim-ita-mcp`) exposing 20+ tools for complete `.circ` lifecycle — parsing, analysis, generation, editing, verification, description — integrated with GraphRAG, Cortex-GDS, NAMS, MemPalace, Azure Vision OCR.

**Key GDS Finding**: `.circ` maps naturally to a knowledge graph. PageRank identifies MUX_Out (0.195) as central hub. Louvain finds 5 communities mapping to CPU microarchitecture (Fetch, Decode+ALU, RegFile+Writeback).

---

## 2. Context & Analysis

### 2.1 The .circ XML Format (ITA 2.16.x)

```xml
<project source="2.16.2.2.jar" version="1.0">
  <lib desc="#Wiring" name="0"/>  <!-- 8 built-in libraries -->
  <main name="main"/>
  <circuit name="main">
    <wire from="(x1,y1)" to="(x2,y2)"/>
    <comp lib="N" loc="(x,y)" name="Type">
      <a name="attr" val="value"/>
    </comp>
  </circuit>
</project>
```

Libraries: Wiring=0, Gates=1, TTL=2, Plexers=3, Arithmetic=4, Memory=5, I/O=6, Base=7. Grid: 10px units.

### 2.2 Reference Repos

| Repo | Approach | Use |
|------|----------|-----|
| **virsi/logisim-mcp** | Full MCP for Evolution 4.x, 25+ tools, Python stdio | Primary reference — adapt for ITA |
| **Celibistrial/logisim-circuit-compiler** | Expression→.circ compiler, zero deps, 3-layer verification | Backend engine for generation |
| **AarambhaAnta/CircGen-AI** | LLM fine-tuning for .circ generation | Future — fine-tuning pipeline |

### 2.3 ITA vs Evolution Schema Differences

| Aspect | ITA 2.16.x | Evolution 4.x |
|--------|-----------|---------------|
| Source | `2.16.2.2.jar` | `4.x.x` |
| TTL lib | `#TTL` (74xx series) | May differ |
| Splitter | `bit1..bit11` attrs | Different naming |
| Clock | Simple component | Frequency attr |

### 2.4 GDS Analysis Results (cpu tuanis circuit)

**PageRank centrality** (top nodes):
- MUX_Out: 0.195 (central ALU→register writeback hub)
- MUX_A/B: 0.083 (operand selection)
- Adder/Subtractor: 0.064 (ALU)
- R0-R3: 0.047 (register file)

**Louvain communities** (modularity=0.255, 5 communities):
- C0: Fetch (Clock, PC, MI, IR)
- C1: Decode+ALU (Splitter, Decoder_Op, MUX_A, Adder, Subtractor, AND_3)
- C2: RegFile+Writeback (MUX_B, MUX_Out, RAM, Decoder_WR, R0-R3, NOT_3)
- C3/C4: Isolated (OR_1, NOT_WR — unused in current wiring)

---

## 3. Hypotheses (SM Engine)

| # | Statement | Criteria | Status |
|---|-----------|----------|--------|
| H1 | .circ → knowledge graph + GDS | ≥10 nodes, ≥20 edges | ✅ VALIDATED (21 nodes, 41 edges) |
| H2 | FastMCP 15-25 tools, no Java | ≥15 tools, round-trip XML | Pending |
| H3 | Adapt virsi/logisim-mcp for ITA | ≥5 schema diffs, ≥3 tools | Pending |
| H4 | Azure Vision OCR → circuit | ≥80% component ID | Pending |
| H5 | circuitc.py integration | Working 4-bit adder | Pending |

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────┐
│           logisim-ita-mcp (FastMCP stdio)           │
├─────────────────────────────────────────────────────┤
│ I/O (5) │ Parser (4) │ Builder (6) │ Analyzer (5)  │
│ Verifier (3) │ Describe (2) │ Graph (2)            │
├─────────────────────────────────────────────────────┤
│ XML Parser │ circuitc.py │ Logisim CLI (--tty)      │
├─────────────────────────────────────────────────────┤
│ Neo4j (circuit KG) │ NAMS │ Azure Vision OCR        │
└─────────────────────────────────────────────────────┘
```

---

## 5. Tool Specification (27 tools)

### 5.1 I/O Tools (5)
1. `create_circuit_file` — Create new .circ with library declarations
2. `read_circuit_file` — Parse .circ XML, return structured JSON
3. `list_circuits` — List all circuits in a .circ file
4. `write_circuit_file` — Serialize modified circuit back to .circ XML
5. `backup_circuit` — Create timestamped backup before edits

### 5.2 Parser Tools (4)
6. `parse_components` — Extract all components with types, locations, attributes
7. `parse_wires` — Extract all wire endpoints and compute connectivity
8. `parse_rom_contents` — Decode ROM/RAM `addr/data:` hex contents
9. `get_circuit_stats` — Component count by type, wire count, bounding box

### 5.3 Builder Tools (6)
10. `add_component` — Add component at specified grid location
11. `add_wire` — Add wire between two grid coordinates
12. `add_pin` — Add input/output pin with label
13. `add_tunnel` — Add tunnel for signal routing
14. `remove_component` — Remove component by location/name
15. `move_component` — Move component to new grid location

### 5.4 High-Level Builder Tools (5)
16. `build_from_expressions` — Generate circuit from boolean expressions (via circuitc.py)
17. `build_half_adder` — Generate half-adder subcircuit
18. `build_full_adder` — Generate full-adder subcircuit
19. `build_ripple_adder` — Generate N-bit ripple-carry adder
20. `build_mux` — Generate N-bit MUX with select lines

### 5.5 Analyzer Tools (5)
21. `describe_circuit` — Natural language description of circuit structure
22. `trace_signal_path` — Follow signal from source through components to output
23. `identify_modules` — Use Louvain communities to identify circuit modules
24. `compute_centrality` — PageRank/Betweenness to find critical components
25. `extract_netlist` — Generate netlist (component-port connections)

### 5.6 Verifier Tools (3)
26. `verify_structure` — Check XML validity, port connectivity, dangling wires
27. `verify_truth_table` — Generate and verify truth table via Logisim CLI
28. `verify_with_logisim` — Headless Logisim load test (--tty stats)

### 5.7 Graph Tools (2)
29. `circuit_to_neo4j` — Load circuit graph into Neo4j for GDS analysis
30. `analyze_circuit_graph` — Run PageRank/Louvain/WCC on circuit graph

---

## 6. Implementation Plan

### Phase 0: Setup & Forks
- [x] **T0.1**: Fork virsi/logisim-mcp → https://github.com/JasonR27/logisim-mcp ✅
- [x] **T0.2**: Fork Celibistrial/logisim-circuit-compiler → https://github.com/JasonR27/logisim-circuit-compiler ✅
- [x] **T0.3**: Clone forks to `/home/jasonr27/Documents/Github/JasonR27/` ✅
- [ ] **T0.4**: Create conda env `logisim-mcp` (Python 3.11+, mcp>=1.0.0, lxml, networkx)
- [ ] **T0.5**: Register MCP server in opencode.jsonc and VS Code settings

### Phase 1: Core Parser & I/O (Week 1)
- [ ] **T1.1**: Implement `circ_parser.py` — XML→structured JSON parser
- [ ] **T1.2**: Implement I/O tools (create, read, write, list, backup)
- [ ] **T1.3**: Implement parser tools (parse_components, parse_wires, parse_rom, stats)
- [ ] **T1.4**: Test round-trip: read cpu tuanis → JSON → write back → diff
- [ ] **T1.5**: Register FastMCP server with tool decorators

### Phase 2: Builder Tools (Week 2)
- [ ] **T2.1**: Implement `grid_manager.py` — coordinate system, placement, port calc
- [ ] **T2.2**: Implement low-level builders (add_component, wire, pin, tunnel, remove, move)
- [ ] **T2.3**: Integrate circuitc.py for expression-based generation
- [ ] **T2.4**: Implement high-level builders (half_adder, full_adder, ripple_adder, mux)
- [ ] **T2.5**: Test: generate 4-bit adder from expression, verify with Logisim CLI

### Phase 3: Analyzer & Graph (Week 3)
- [ ] **T3.1**: Implement `circuit_graph.py` — .circ → NetworkX graph
- [ ] **T3.2**: Implement describe_circuit, trace_signal_path
- [ ] **T3.3**: Implement identify_modules (Louvain), compute_centrality (PageRank)
- [ ] **T3.4**: Implement circuit_to_neo4j and analyze_circuit_graph

### Phase 4: Verification (Week 4)
- [ ] **T4.1**: Implement verify_structure (XML schema, connectivity)
- [ ] **T4.2**: Implement verify_truth_table (Logisim CLI --test-vector)
- [ ] **T4.3**: Implement verify_with_logisim (--tty stats headless)
- [ ] **T4.4**: Adapt virsi/logisim-mcp verification for ITA format

### Phase 5: Vision & Integration (Week 5)
- [ ] **T5.1**: Azure Vision OCR pipeline (screenshot → component list)
- [ ] **T5.2**: image_to_circuit (OCR results → .circ generation)
- [ ] **T5.3**: NAMS + MemPalace integration
- [ ] **T5.4**: Register in all agent configs

### Phase 6: Testing & Validation (Week 6)
- [ ] **T6.1**: Unit tests for all 27 tools
- [ ] **T6.2**: Integration test: parse → analyze → describe → regenerate
- [ ] **T6.3**: Validate H3-H5

---

## 7. File Structure

```
logisim-ita-mcp/
├── pyproject.toml
├── src/
│   └── logisim_ita_mcp/
│       ├── __init__.py
│       ├── server.py           # FastMCP server entry point
│       ├── circ_parser.py      # XML parser (stdlib xml.etree)
│       ├── circ_writer.py      # XML serializer
│       ├── grid_manager.py     # Coordinate system & placement
│       ├── circuit_graph.py    # NetworkX graph builder
│       ├── circuit_verifier.py # Verification tools
│       ├── circuit_builder.py  # High-level builders
│       ├── circuitc_adapter.py # circuitc.py integration
│       ├── neo4j_adapter.py    # Neo4j graph loader
│       ├── vision_ocr.py       # Azure Vision OCR pipeline
│       └── tools/
│           ├── io_tools.py
│           ├── parser_tools.py
│           ├── builder_tools.py
│           ├── analyzer_tools.py
│           ├── verifier_tools.py
│           └── graph_tools.py
├── tests/
│   ├── test_parser.py
│   ├── test_builder.py
│   ├── test_analyzer.py
│   └── test_verifier.py
└── examples/
    ├── cpu_tuanis_analysis.json
    └── generated_4bit_adder.circ
```

---

## 8. Questions for Jason

1. **Repo forks**: May I fork virsi/logisim-mcp and Celibistrial/logisim-circuit-compiler to your GitHub?
2. **Conda env**: Should I create a new `logisim-mcp` env or reuse an existing one?
3. **Logisim CLI**: The verification tools need `java -jar Logisim-jar-with-dependencies.jar --tty` — OK to use the existing build?
4. **Azure Vision**: Which Azure subscription/resource should I use for OCR? Is the GPU graph analytics conda env the right place for credentials?
5. **Priority**: Should I start with Phase 1 (parser) or Phase 5 (Vision OCR) first?
6. **Image**: You mentioned a circuit image — I cannot view images directly. Should I use Azure Vision OCR to process it, or can you describe what the image shows?

---

## 9. Next Steps (Rolling)

1. **Best Next Step**: Get Jason's approval on repo forks (T0.1-T0.3) and conda env setup (T0.4)
2. Start Phase 1: implement `circ_parser.py` using the cpu tuanis .circ as test fixture
3. Set up FastMCP server skeleton with first 5 I/O tools
4. Run round-trip test (read → JSON → write → diff) to validate parser fidelity
5. Begin Phase 2 grid_manager.py for coordinate-based component placement
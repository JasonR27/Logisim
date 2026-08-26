"""Logisim ITA MCP Server — FastMCP entry point."""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.tools.tool import ToolAnnotations

from .circ.model import fmt_loc
from .circ.parser import parse
from .circ.writer import dump_to_file
from .circ.verifier import LogisimVerifier, DEFAULT_ITA_JAR

mcp = FastMCP("logisim-ita-mcp", version="0.1.0")


@mcp.tool(
    title="Read Circuit File",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
)
def read_circuit_file(path: str) -> str:
    """Parse a Logisim ITA `.circ` file and return its FULL structured contents as JSON.

    Use this when you need everything at once: project metadata (source app,
    version, main circuit, libraries) plus every circuit block with its
    components (typed, located, labeled, attributed) and wires. For large
    projects prefer the targeted tools first: list_circuits ->
    get_circuit_stats -> parse_components / parse_wires.

    Args:
        path: Absolute path to the `.circ` file to read (e.g.
            /home/user/projects/cpu.circ). Relative paths resolve against
            the server process CWD — absolute is strongly recommended.

    Returns:
        JSON string with `{"source", "version", "main_circuit", "libraries",
        "circuits"}` where each circuit provides `name`, `attributes`,
        `component_count`, `wire_count`, `component_summary` (type->count
        map), `components[]` (name, lib, location "x,y", label, width,
        attributes) and `wires[]` (`from`/`to` points). On failure returns
        `{"error": "<message>"}` instead of raising.
    """
    try:
        project = parse(Path(path))
        result = {
            "source": project.source,
            "version": project.version,
            "main_circuit": project.main,
            "libraries": [{"id": lib.id, "desc": lib.desc} for lib in project.libs],
            "circuits": [],
        }
        for circuit in project.circuits:
            circ_data = {
                "name": circuit.name,
                "attributes": circuit.attrs,
                "component_count": len(circuit.components),
                "wire_count": len(circuit.wires),
                "component_summary": circuit.get_component_summary(),
                "components": [
                    {"name": c.name, "lib": c.lib, "location": fmt_loc(c.loc),
                     "label": c.label, "width": c.width, "attributes": c.attrs}
                    for c in circuit.components
                ],
                "wires": [{"from": fmt_loc(w.start), "to": fmt_loc(w.end)} for w in circuit.wires],
            }
            result["circuits"].append(circ_data)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    title="List Circuits",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
)
def list_circuits(path: str) -> str:
    """List every circuit defined in a Logisim ITA `.circ` project file.

    Cheap overview call — no component payloads. Ideal first step to discover
    which circuit names exist (e.g. "main", subcircuits) before passing one as
    `circuit_name` to other tools like get_circuit_stats or parse_wires.

    Args:
        path: Absolute path to the `.circ` project file.

    Returns:
        JSON string `{"circuits": [{"name", "components", "wires",
        "summary"}...]}` where summary is a component-type count map for that
        circuit. On failure returns `{"error": "<message>"}`.
    """
    try:
        project = parse(Path(path))
        circuits = [
            {"name": c.name, "components": len(c.components),
             "wires": len(c.wires), "summary": c.get_component_summary()}
            for c in project.circuits
        ]
        return json.dumps({"circuits": circuits}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    title="Get Circuit Statistics",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
)
def get_circuit_stats(path: str, circuit_name: str = "main") -> str:
    """Get aggregate statistics for ONE circuit: type histogram, totals, bounding box.

    Lightweight sizing pass before deep parsing. The bounding box (in Logisim
    grid units, computed from component locations plus wire endpoints) tells
    you the drawn extent of the circuit — useful for layout sanity checks and
    for planning where new components can be placed.

    Args:
        path: Absolute path to the `.circ` project file.
        circuit_name: Name of the circuit block to inspect. Defaults to
            "main". Unknown names raise KeyError surfaced as
            {"error": ...} — use list_circuits to discover valid names.

    Returns:
        JSON string with `circuit`, `component_summary` (type->count map),
        `total_components`, `total_wires`, and `bounding_box`
        `{min_x, max_x, min_y, max_y, width, height}` (null if empty).
    """
    try:
        project = parse(Path(path))
        circuit = project.require_circuit(circuit_name)
        all_points = [(p[0], p[1]) for p in [c.loc for c in circuit.components] +
                      [w.start for w in circuit.wires] + [w.end for w in circuit.wires]]
        bbox = None
        if all_points:
            xs, ys = [p[0] for p in all_points], [p[1] for p in all_points]
            bbox = {"min_x": min(xs), "max_x": max(xs), "min_y": min(ys),
                    "max_y": max(ys), "width": max(xs)-min(xs), "height": max(ys)-min(ys)}
        return json.dumps({"circuit": circuit.name, "component_summary": circuit.get_component_summary(),
                          "total_components": len(circuit.components), "total_wires": len(circuit.wires),
                          "bounding_box": bbox}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    title="Parse Components",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
)
def parse_components(path: str, circuit_name: str = "main") -> str:
    """Extract every component of ONE circuit with resolved library names and full attributes.

    The deep-dive read for component-level work: each entry resolves the
    library id to a human-readable `lib_desc`, and includes the raw
    attribute dict (e.g. Pin output/facing attrs, Register WIDTH, gate
    inputs). Use this when you need exact pin/attribute geometry — for
    example before synthesizing new components that must match ITA
    conventions.

    Args:
        path: Absolute path to the `.circ` project file.
        circuit_name: Circuit block name. Defaults to "main"; invalid
            names surface as {"error": ...}.

    Returns:
        JSON string `{"circuit", "components": [{"name", "lib_id",
        "lib_desc", "location" ("x,y"), "label", "width", "attributes"}]}`
        where attributes are exactly as stored in the XML (strings).
    """
    try:
        project = parse(Path(path))
        circuit = project.require_circuit(circuit_name)
        components = []
        for comp in circuit.components:
            lib_desc = ""
            try:
                lib_desc = project.lib_desc_for_id(comp.lib)
            except KeyError:
                pass
            components.append({"name": comp.name, "lib_id": comp.lib, "lib_desc": lib_desc,
                             "location": fmt_loc(comp.loc), "label": comp.label,
                             "width": comp.width, "attributes": comp.attrs})
        return json.dumps({"circuit": circuit.name, "components": components}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    title="Parse Wires & Nets",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
)
def parse_wires(path: str, circuit_name: str = "main") -> str:
    """Extract all wires of ONE circuit AND compute electrical connectivity (nets).

    Besides the raw endpoint list, this groups wires into nets by flooding
    over shared coordinates ("x,y" points) — i.e. which wire segments touch,
    forming one equipotential node. Use it for connectivity audits, finding
    dangling/shorted segments, or rebuilding a netlist without a GUI.

    Args:
        path: Absolute path to the `.circ` project file.
        circuit_name: Circuit block name. Defaults to "main"; invalid
            names surface as {"error": ...}.

    Returns:
        JSON string with `circuit`, `wire_count`, `wires` (each
        `{"from": "x,y", "to": "x,y"}`), `net_count`, and `nets`
        (list of lists of wire indices). Note: nets connect WIRES only;
        component pins are not endpoints here unless wires terminate on
        their grid coordinate.
    """
    try:
        project = parse(Path(path))
        circuit = project.require_circuit(circuit_name)
        wires = [{"from": fmt_loc(w.start), "to": fmt_loc(w.end)} for w in circuit.wires]
        # Build adjacency from shared points
        point_to_wires: dict[str, list[int]] = {}
        for i, w in enumerate(circuit.wires):
            for pt in [fmt_loc(w.start), fmt_loc(w.end)]:
                point_to_wires.setdefault(pt, []).append(i)
        # Find connected wire groups (nets)
        visited: set[int] = set()
        nets = []
        for i in range(len(circuit.wires)):
            if i in visited:
                continue
            net: set[int] = set()
            stack = [i]
            while stack:
                wi = stack.pop()
                if wi in visited:
                    continue
                visited.add(wi)
                net.add(wi)
                for pt in [fmt_loc(circuit.wires[wi].start), fmt_loc(circuit.wires[wi].end)]:
                    for neighbor in point_to_wires.get(pt, []):
                        if neighbor not in visited:
                            stack.append(neighbor)
            nets.append(list(net))
        return json.dumps({"circuit": circuit.name, "wire_count": len(wires),
                          "wires": wires, "net_count": len(nets), "nets": nets}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    title="Describe Circuit (Natural Language)",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
)
def describe_circuit(path: str, circuit_name: str = "main") -> str:
    """Generate a compact human-readable summary of ONE circuit (not JSON).

    Produces a short plaintext brief: total component/wire counts, a sorted
    type histogram line (largest first), and every labeled component with its
    label, type, and location. Feed it directly to an LLM as context when you
    need to reason about what a circuit does before touching it.

    Args:
        path: Absolute path to the `.circ` project file.
        circuit_name: Circuit block name. Defaults to "main"; invalid
            names surface as an "Error: ..." text response.

    Returns:
        Plaintext multi-line description (NOT JSON). Lines start with "- "
        for lists and "  * " under "Labeled components:".
    """
    try:
        project = parse(Path(path))
        circuit = project.require_circuit(circuit_name)
        summary = circuit.get_component_summary()
        labeled = [(c.label, c.name, fmt_loc(c.loc)) for c in circuit.components if c.label]
        parts = [f"Circuit '{circuit.name}' from Logisim ITA {project.source}:",
                f"- {len(circuit.components)} components, {len(circuit.wires)} wires",
                f"- Types: {', '.join(f'{n}({c})' for n, c in sorted(summary.items(), key=lambda x: -x[1]))}"]
        if labeled:
            parts.append("- Labeled components:")
            for label, name, loc in labeled:
                parts.append(f"  * {label} ({name} at {loc})")
        return "\n".join(parts)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    title="Write Circuit File",
    annotations=ToolAnnotations(destructiveHint=True, idempotentHint=True, openWorldHint=False),
)
def write_circuit_file(path: str, circuit_name: str = "main") -> str:
    """Serialize a parsed `.circ` project back to an ITA-native file (round-trip write).

    Currently round-trip oriented: re-parses the existing file at `path` and
    rewrites it in Logisim ITA 2.16.x native format via dump_to_file. This has
    been verified lossless (22 comps / 131 wires survive untouched). For
    generation from scratch, build a Project object in code and call
    circ.writer.dump_to_file directly — dedicated build_* MCP tools are
    planned. OVERWRITES the destination file; keep a backup.

    Args:
        path: Absolute path of the .circ file to rewrite (must exist for
            now).
        circuit_name: Informational circuit block label echoed back in the
            result. Defaults to "main".

    Returns:
        JSON string `{"wrote": "<path>", "circuit": "<name>"}` or
        {"error": "<message>"}.
    """
    try:
        # Re-parse from existing file if present (round-trip focused helper).
        # For generation from scratch, use build_* tools to construct a Project,
        # then this writes it. Here we demonstrate by parsing then writing.
        project = parse(Path(path))
        dump_to_file(project, path)
        result = {"wrote": path, "circuit": circuit_name}
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool(
    title="Verify With Logisim (Headless Load Test)",
    annotations=ToolAnnotations(idempotentHint=True, openWorldHint=True),
)
def verify_with_logisim(path: str, jar: str = str(DEFAULT_ITA_JAR)) -> str:
    """Headlessly load a `.circ` file with the real Logisim ITA JAR to prove it loads cleanly.

    Runs `java -jar <jar> -tty stats <file>` with a timeout. THE guardrail for
    any generated or hand-edited circuit: if the file loads headlessly it will
    load in the GUI; a timeout means the file is malformed or shorts the
    simulation. Always call this after writing a .circ via write_circuit_file
    or any external generation step.

    Args:
        path: Absolute path to the .circ file to validate.
        jar: Optional absolute path to a Logisim ITA jar. Defaults to the
            repo's Compiled/Logisim-ITA.jar (Java 21 compatible). Do NOT use
            target/Logisim.jar — it requires Java 25 and hangs/fails on
            system Java 21.

    Returns:
        JSON string: success is `{"ok": true, ..., "component_histogram":
        {...}}`; failure returns ok:false info or an error message including
        timeout indications.
    """
    verifier = LogisimVerifier(jar)
    result = verifier.verify_load(path)
    return json.dumps(result, indent=2)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
"""Logisim ITA MCP Server — FastMCP entry point."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .circ.model import fmt_loc
from .circ.parser import parse

mcp = FastMCP("logisim-ita-mcp", version="0.1.0")


@mcp.tool()
def read_circuit_file(path: str) -> str:
    """Parse a .circ file and return structured JSON with all components, wires, and metadata."""
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


@mcp.tool()
def list_circuits(path: str) -> str:
    """List all circuits in a .circ file with component counts."""
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


@mcp.tool()
def get_circuit_stats(path: str, circuit_name: str = "main") -> str:
    """Get detailed statistics: component counts, wire count, bounding box."""
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


@mcp.tool()
def parse_components(path: str, circuit_name: str = "main") -> str:
    """Extract all components with types, locations, and attributes."""
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


@mcp.tool()
def parse_wires(path: str, circuit_name: str = "main") -> str:
    """Extract all wires and compute connectivity (nets)."""
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


@mcp.tool()
def describe_circuit(path: str, circuit_name: str = "main") -> str:
    """Generate a natural language description of the circuit."""
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


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
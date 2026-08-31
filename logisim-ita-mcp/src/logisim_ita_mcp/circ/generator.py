"""From-scratch .circ generation: JSON spec -> Project -> file.

The single sanctioned path for building circuits without hand-editing XML.
Delegates all serialization invariants to circ.writer (subcircuit lib rule,
L-shaped wire split, multi-line attrs) so generated files inherit every
known load guarantee.
"""

from __future__ import annotations

from pathlib import Path

from .model import Circuit, Component, Lib, Project, Wire, parse_loc
from .writer import dump_to_file

# Presets captured from the working reference test_registros8_v1.circ
ITA_STANDARD_LIBS = [
    {"id": "0", "desc": "#Wiring"},
    {"id": "1", "desc": "#Gates"},
    {"id": "2", "desc": "#TTL"},
    {"id": "3", "desc": "#Plexers"},
    {"id": "4", "desc": "#Arithmetic"},
    {"id": "5", "desc": "#Memory"},
    {"id": "6", "desc": "#I/O"},
    {"id": "7", "desc": "#Base"},
]

ITA_STANDARD_EXTRAS = [
    # Exact pretty-printed form used by Logisim ITA when saving (byte-faithful).
    '<options>\n    <a name="gateUndefined" val="ignore"/>\n    <a name="simlimit" val="1000"/>\n'
    '    <a name="simrand" val="0"/>\n  </options>',
    '<mappings>\n    <tool lib="7" map="Button2" name="Poke Tool"/>\n'
    '    <tool lib="7" map="Button3" name="Menu Tool"/>\n'
    '    <tool lib="7" map="Ctrl Button1" name="Menu Tool"/>\n  </mappings>',
    '<toolbar>\n    <tool lib="7" name="Poke Tool"/>\n    <tool lib="7" name="Edit Tool"/>\n    <sep/>\n'
    '    <tool lib="0" name="Pin"><a name="tristate" val="false"/></tool>\n'
    '    <tool lib="0" name="Pin"><a name="facing" val="west"/><a name="output" val="true"/></tool>\n'
    '    <tool lib="1" name="NOT Gate"/>\n    <tool lib="1" name="AND Gate"/>\n'
    '    <tool lib="1" name="OR Gate"/>\n  </toolbar>',
]


def _loc(raw, where: str) -> tuple[int, int]:
    if isinstance(raw, str):
        return parse_loc(raw)
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        return int(raw[0]), int(raw[1])
    raise ValueError(f"{where}: invalid loc {raw!r} (want \"(x,y)\" or [x, y])")



def generate_project(spec: dict) -> Project:
    """Build a Project from a spec dict. Raises ValueError on invalid input."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object")

    circuits_spec = spec.get("circuits")
    if not isinstance(circuits_spec, list) or not circuits_spec:
        raise ValueError("spec.circuits must be a non-empty list")

    project = Project(
        source=str(spec.get("source", "2.16.2.2.jar")),
        version=str(spec.get("version", "1.0")),
        main=str(spec.get("main", "main")),
    )

    libs_spec = spec.get("libraries", "standard")
    if libs_spec == "standard":
        libs_spec = [dict(l) for l in ITA_STANDARD_LIBS]
    if not isinstance(libs_spec, list) or not libs_spec:
        raise ValueError("spec.libraries must be 'standard' or a non-empty list")
    for lib in libs_spec:
        if not isinstance(lib, dict) or "id" not in lib or "desc" not in lib:
            raise ValueError(f"library entry needs 'id' and 'desc': {lib}")
        project.libs.append(Lib(
            id=str(lib["id"]),
            desc=str(lib["desc"]),
            tools_raw_xml=list(lib.get("tools_raw_xml", [])),
        ))

    extras_spec = spec.get("extras_raw_xml", "standard")
    if extras_spec == "standard":
        extras_spec = list(ITA_STANDARD_EXTRAS)
    if isinstance(extras_spec, list):
        # BUGFIX 2026-08-31: extras were previously computed but never applied
        # (the application block sat unreachable after `return` in
        # spec_from_file). Without them Logisim ITA silently substitutes its
        # default options/mappings/toolbar, which changes the GUI toolbar and
        # shifts the canvas ~19px — breaking strict byte/pixel fidelity.
        project.extras_raw_xml.extend(str(raw) for raw in extras_spec if raw)

    for c in circuits_spec:
        if not isinstance(c, dict) or "name" not in c:
            raise ValueError("each circuits entry needs a 'name'")
        circuit = Circuit(name=str(c["name"]), attrs={
            str(k): str(v) for k, v in (c.get("attributes") or {}).items()
        })
        comps_spec = c.get("components", [])
        if not isinstance(comps_spec, list):
            raise ValueError(f"circuit {circuit.name!r}: components must be a list")
        for comp in comps_spec:
            if not isinstance(comp, dict) or "name" not in comp or "loc" not in comp:
                raise ValueError(f"circuit {circuit.name!r}: each component needs 'name' and 'loc'")
            loc = _loc(comp["loc"], f"circuit {circuit.name!r} component {comp['name']!r}")
            lib_val = comp.get("lib")
            # Subcircuit instance rule: NO lib attribute when the component
            # name matches a circuit defined in this same spec.
            lib_str = None if lib_val in (None, "") else str(lib_val)
            circuit.components.append(Component(
                lib=lib_str,
                name=str(comp["name"]),
                loc=loc,
                attrs={str(k): str(v) for k, v in (comp.get("attributes") or {}).items()},
            ))
        wires_spec = c.get("wires", [])
        if not isinstance(wires_spec, list):
            raise ValueError(f"circuit {circuit.name!r}: wires must be a list")
        for w in wires_spec:
            if isinstance(w, dict):
                start_raw, end_raw = w.get("from"), w.get("to")
            elif isinstance(w, (list, tuple)) and len(w) == 2:
                start_raw, end_raw = w[0], w[1]
            else:
                raise ValueError(
                    f"circuit {circuit.name!r}: wire must be [from, to] or {{from, to}}; got {w!r}"
                )
            start = _loc(start_raw, f"circuit {circuit.name!r} wire")
            end = _loc(end_raw, f"circuit {circuit.name!r} wire")
            if start == end:
                raise ValueError(
                    f"circuit {circuit.name!r}: zero-length wire at {start} (Logisim ITA rejects it)"
                )
            circuit.wires.append(Wire(start=start, end=end))
        project.circuits.append(circuit)

    return project


def generate_to_file(spec: dict, path: str) -> dict:
    """Generate from spec and write to `path`. Returns a summary dict."""
    project = generate_project(spec)
    dump_to_file(project, path)
    return {
        "wrote": path,
        "main": project.main,
        "circuits": [
            {"name": circ.name, "components": len(circ.components), "wires": len(circ.wires)}
            for circ in project.circuits
        ],
    }


def spec_from_file(reference_path: str) -> dict:
    """Build a generation spec by parsing an existing .circ file.

    Convenience for the recreate-from-reference workflow: the output spec
    reproduces the reference exactly when fed back through generate_to_file.
    """
    from .parser import parse

    project = parse(Path(reference_path))
    return {
        "source": project.source,
        "version": project.version,
        "main": project.main,
        "libraries": [
            {"id": lib.id, "desc": lib.desc, "tools_raw_xml": list(lib.tools_raw_xml)}
            for lib in project.libs
        ],
        "extras_raw_xml": list(project.extras_raw_xml) or "standard",
        "circuits": [
            {
                "name": circ.name,
                "attributes": dict(circ.attrs),
                "components": [
                    {"name": comp.name, "lib": comp.lib, "loc": f"({comp.loc[0]},{comp.loc[1]})",
                     "attributes": dict(comp.attrs)}
                    for comp in circ.components
                ],
                "wires": [
                    {"from": f"({w.start[0]},{w.start[1]})", "to": f"({w.end[0]},{w.end[1]})"}
                    for w in circ.wires
                ],
            }
            for circ in project.circuits
        ],
    }


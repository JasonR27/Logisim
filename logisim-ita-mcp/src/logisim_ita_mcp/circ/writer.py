"""Serialize a Logisim ITA model back to .circ XML.

Targets Logisim ITA 2.16.x schema exactly (source="2.16.2.2.jar",
classic library system). Round-trips the original circuit so the
parser+writer are lossless, then supports new generation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Circuit, Component, Lib, Project, Wire, fmt_loc, wire_l_path


@dataclass
class WriterOptions:
    """Options controlling output fidelity."""
    indent: str = "    "
    header_text: str = "This file is intended to be loaded by Logisim http://logisim.altervista.org"


class CircuitWriter:
    """Serialize a Project to ITA .circ XML."""

    def __init__(self) -> None:
        self._opts = WriterOptions()
        self._out: list[str] = []

    def write(self, project: Project) -> str:
        self._out = []
        self._normalize_subcircuit_libs(project)
        self._line('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
        self._line(f'<project source="{project.source}" version="{project.version}">')
        if project.leading_text:
            self._line(f'  {project.leading_text}')
        else:
            self._line(f'  {self._opts.header_text}')
        for lib in project.libs:
            self._write_lib(lib)
        self._line(f'  <main name="{project.main}"/>')
        # options/mappings/toolbar preserved as raw XML if present
        for raw in project.extras_raw_xml:
            self._line(f"  {raw}")
        for circuit in project.circuits:
            self._write_circuit(circuit)
        self._line('</project>')
        return "\n".join(self._out)

    def _normalize_subcircuit_libs(self, project: Project) -> None:
        """Strip the ``lib`` attribute from subcircuit instances.

        A ``<comp>`` whose name matches a circuit defined in this file is a
        subcircuit instance and must carry NO ``lib`` attribute: Logisim's
        ``findLibrary()`` resolves it against the file itself. Carrying
        e.g. ``lib="7"`` makes the loader look inside library 7 (Base) and
        fail with "component 'X' missing from library", which surfaces as a
        modal error dialog during load.
        """
        circuit_names = {c.name for c in project.circuits}
        for circuit in project.circuits:
            for comp in circuit.components:
                if comp.lib and comp.name in circuit_names:
                    comp.lib = None

    def _write_lib(self, lib: Lib) -> None:
        if lib.tools_raw_xml:
            self._line(f'  <lib desc="{lib.desc}" name="{lib.id}">')
            for raw in lib.tools_raw_xml:
                self._line(f"    {raw}")
            self._line("  </lib>")
        else:
            self._line(f'  <lib desc="{lib.desc}" name="{lib.id}"/>')

    def _write_circuit(self, circuit: Circuit) -> None:
        self._line(f'  <circuit name="{circuit.name}">')
        for name, val in circuit.attrs.items():
            self._line(self._attr_xml(name, val, indent="    "))
        # wires first (matching ITA convention)
        for wire in circuit.wires:
            self._write_wire(wire)
        # then components
        for comp in circuit.components:
            self._write_component(comp)
        for raw in circuit.extras_raw_xml:
            self._line(f"    {raw}")
        self._line("  </circuit>")

    def _write_wire(self, wire: Wire) -> None:
        # Logisim ITA cannot load diagonal wires (WireRepair.doOverlaps hangs).
        # The single source of truth for the axis-aligned L-split lives in
        # model.wire_l_path — the same helper every generation tool must use.
        for segment in wire_l_path(wire.start, wire.end):
            self._line(f'    <wire from="{fmt_loc(segment.start)}" to="{fmt_loc(segment.end)}"/>')

    def _write_component(self, comp: Component) -> None:
        # ITA schema: subcircuit instances use NO lib attribute (empty string).
        # When lib is null/empty, Logisim's findLibrary() returns the file itself,
        # which contains all circuits as tools. Using lib="7" looks in the Base
        # library which does NOT contain subcircuits — causes "missing from library"
        # errors. Only builtin/external components carry lib="N".
        attrs_part = f' lib="{comp.lib}"' if comp.lib else ""
        tag = f'    <comp{attrs_part} loc="{fmt_loc(comp.loc)}" name="{comp.name}"'
        if not comp.attrs:
            self._line(tag + "/>")
            return
        self._line(tag + ">")
        for name, val in comp.attrs.items():
            self._line(self._attr_xml(name, val, indent="      "))
        self._line("    </comp>")

    @staticmethod
    def _attr_xml(name: str, val: str, indent: str) -> str:
        """Serialize one <a> attribute.

        Single-line values -> `val="..."` attribute form (ITA convention).
        Multi-line values (ROM/RAM 'contents', etc.) MUST use element-text
        form `<a name="x">
line1
line2</a>` because XML attribute-value
        normalization folds newlines into spaces — writing them as val=
        silently corrupts data.
        """
        esc = (val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                  .replace('"', "&quot;"))
        if "\n" not in val:
            return f'{indent}<a name="{name}" val="{esc}"/>'
        inner = val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'{indent}<a name="{name}">{inner}</a>'

    def _line(self, text: str) -> None:
        self._out.append(text)


def dump(project: Project) -> str:
    """Convenience: serialize a Project to a .circ XML string."""
    return CircuitWriter().write(project)


def dump_to_file(project: Project, path: str) -> None:
    """Serialize a Project to a .circ file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(dump(project))
        f.write("\n")

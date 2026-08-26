"""Serialize a Logisim ITA model back to .circ XML.

Targets Logisim ITA 2.16.x schema exactly (source="2.16.2.2.jar",
classic library system). Round-trips the original circuit so the
parser+writer are lossless, then supports new generation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import Circuit, Component, Lib, Project, Wire, fmt_loc


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
            self._line(f'    <a name="{name}" val="{val}"/>')
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
        self._line(f'    <wire from="{fmt_loc(wire.start)}" to="{fmt_loc(wire.end)}"/>')

    def _write_component(self, comp: Component) -> None:
        # base tag
        tag = f'    <comp lib="{comp.lib}" loc="{fmt_loc(comp.loc)}" name="{comp.name}"'
        if not comp.attrs:
            self._line(tag + "/>")
            return
        self._line(tag + ">")
        for name, val in comp.attrs.items():
            self._line(f'      <a name="{name}" val="{val}"/>')
        self._line("    </comp>")

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
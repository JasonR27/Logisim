"""Data model for a Logisim ITA .circ project.

Adapted from virsi/logisim-mcp for Logisim ITA 2.16.x format.
Preserves unknown elements as raw XML for faithful round-trip.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Point = tuple[int, int]


def parse_loc(raw: str) -> Point:
    """Parse a Logisim location string ``(x,y)`` into a tuple of ints."""
    s = raw.strip()
    if not (s.startswith("(") and s.endswith(")")):
        raise ValueError(f"invalid loc: {raw!r}")
    x_str, _, y_str = s[1:-1].partition(",")
    return int(x_str.strip()), int(y_str.strip())


def fmt_loc(point: Point) -> str:
    """Format a point as ``(x,y)`` — Logisim's canonical form."""
    return f"({point[0]},{point[1]})"


@dataclass
class Lib:
    """A ``<lib desc="…" name="ID">`` entry."""
    id: str
    desc: str
    tools_raw_xml: list[str] = field(default_factory=list)


@dataclass
class Component:
    """A ``<comp lib="L" loc="(x,y)" name="N">`` with its ``<a>`` attributes."""
    lib: str
    name: str
    loc: Point
    attrs: dict[str, str] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.name}@{fmt_loc(self.loc)}"

    @property
    def width(self) -> int:
        """Return bit width from attributes (default 1)."""
        return int(self.attrs.get("width", "1"))

    @property
    def label(self) -> str:
        return self.attrs.get("label", "")


@dataclass
class Wire:
    """A ``<wire from="(x1,y1)" to="(x2,y2)"/>`` segment."""
    start: Point
    end: Point


@dataclass
class Circuit:
    """A ``<circuit name="…">`` block."""
    name: str
    attrs: dict[str, str] = field(default_factory=dict)
    components: list[Component] = field(default_factory=list)
    wires: list[Wire] = field(default_factory=list)
    extras_raw_xml: list[str] = field(default_factory=list)

    def find_component(self, loc: Point) -> Component | None:
        for c in self.components:
            if c.loc == loc:
                return c
        return None

    def find_components_by_name(self, name: str) -> list[Component]:
        return [c for c in self.components if c.name == name]

    def find_components_by_label(self, label: str) -> list[Component]:
        return [c for c in self.components if c.label == label]

    def get_component_summary(self) -> dict[str, int]:
        """Return count of each component type."""
        summary: dict[str, int] = {}
        for c in self.components:
            summary[c.name] = summary.get(c.name, 0) + 1
        return summary


@dataclass
class Project:
    """The whole ``<project>`` document."""
    source: str = "2.16.2.2"
    version: str = "1.0"
    libs: list[Lib] = field(default_factory=list)
    main: str = "main"
    circuits: list[Circuit] = field(default_factory=list)
    extras_raw_xml: list[str] = field(default_factory=list)
    leading_text: str | None = None

    def lib_id_for_desc(self, desc: str) -> str:
        for lib in self.libs:
            if lib.desc == desc:
                return lib.id
        raise KeyError(f"library {desc!r} not present in project")

    def lib_desc_for_id(self, lib_id: str) -> str:
        for lib in self.libs:
            if lib.id == lib_id:
                return lib.desc
        raise KeyError(f"library id {lib_id!r} not present in project")

    def find_circuit(self, name: str) -> Circuit | None:
        for c in self.circuits:
            if c.name == name:
                return c
        return None

    def require_circuit(self, name: str) -> Circuit:
        c = self.find_circuit(name)
        if c is None:
            raise KeyError(f"circuit {name!r} not found")
        return c
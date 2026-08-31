"""Regression test: the writer must never emit diagonal <wire> segments.

A diagonal wire (both x and y differ between `from` and `to`) in the `main`
circuit causes the Logisim GUI to hang on load. The writer must split any
diagonal wire into two axis-aligned L-shaped segments (horizontal then
vertical, corner at (end.x, start.y)) so the output only ever contains
axis-aligned wires.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# The package is a plain src-layout with no install metadata; make the
# source tree importable when running pytest from the repo root.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from logisim_ita_mcp.circ.model import Circuit, Project, Wire  # noqa: E402
from logisim_ita_mcp.circ.writer import dump  # noqa: E402

_WIRE_RE = re.compile(
    r'<wire from="\((-?\d+),(-?\d+)\)" to="\((-?\d+),(-?\d+)\)"'
)


def _extract_wires(xml: str) -> list[tuple[int, int, int, int]]:
    """Return (x1, y1, x2, y2) for every <wire> in the serialized XML."""
    return [
        (int(x1), int(y1), int(x2), int(y2))
        for x1, y1, x2, y2 in _WIRE_RE.findall(xml)
    ]


def _diagonals(wires: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    return [w for w in wires if w[0] != w[2] and w[1] != w[3]]


def _make_project(wires: list[Wire]) -> Project:
    proj = Project()
    proj.circuits.append(Circuit(name="main", wires=wires))
    return proj


def test_diagonal_wire_is_split_into_two_axis_aligned_segments() -> None:
    """A diagonal wire becomes two L-shaped segments with no diagonal."""
    proj = _make_project([Wire(start=(560, 200), end=(1040, 0))])
    xml = dump(proj)
    wires = _extract_wires(xml)

    assert len(wires) == 2, f"expected 2 segments, got {len(wires)}: {wires}"
    assert _diagonals(wires) == [], f"diagonal segments remain: {_diagonals(wires)}"

    # Horizontal segment first: (560,200) -> (1040,200)
    assert wires[0] == (560, 200, 1040, 200), wires
    # Vertical segment second: (1040,200) -> (1040,0)
    assert wires[1] == (1040, 200, 1040, 0), wires


def test_axis_aligned_wires_pass_through_unchanged() -> None:
    """Horizontal and vertical wires are emitted as-is (no spurious splits)."""
    proj = _make_project([
        Wire(start=(0, 0), end=(100, 0)),    # horizontal
        Wire(start=(50, 10), end=(50, 90)),  # vertical
    ])
    xml = dump(proj)
    wires = _extract_wires(xml)

    assert wires == [(0, 0, 100, 0), (50, 10, 50, 90)], wires
    assert _diagonals(wires) == []


def test_mixed_wires_never_emit_diagonals() -> None:
    """A mix of diagonal and axis-aligned wires yields zero diagonals."""
    proj = _make_project([
        Wire(start=(560, 200), end=(1040, 0)),   # diagonal
        Wire(start=(0, 0), end=(100, 0)),        # horizontal
        Wire(start=(560, 210), end=(1040, 45)),  # diagonal
    ])
    xml = dump(proj)
    wires = _extract_wires(xml)

    # 2 diagonals -> 4 segments, plus 1 horizontal = 5 total
    assert len(wires) == 5, wires
    assert _diagonals(wires) == [], f"diagonal segments remain: {_diagonals(wires)}"


def test_zero_length_wire_is_emitted_as_single_segment() -> None:
    """A degenerate (zero-length) wire is not a diagonal and stays single."""
    proj = _make_project([Wire(start=(10, 10), end=(10, 10))])
    xml = dump(proj)
    wires = _extract_wires(xml)

    assert wires == [(10, 10, 10, 10)], wires
    assert _diagonals(wires) == []


def test_subcircuit_instance_lib_attribute_is_stripped() -> None:
    """A comp whose name matches a circuit in the file must carry no lib.

    Subcircuit instances with e.g. lib="7" make Logisim's loader fail with
    "component 'X' missing from library" (a modal dialog that blocks load).
    The writer normalizes them by dropping the lib attribute.
    """
    from logisim_ita_mcp.circ.model import Component

    sub = Component(loc=(560, 200), name="REGISTROS8", lib="7")
    proj = Project()
    proj.circuits.append(Circuit(name="REGISTROS8"))
    proj.circuits.append(Circuit(name="main", components=[sub]))

    xml = dump(proj)

    # The subcircuit instance must have no lib attribute...
    assert '<comp loc="(560,200)" name="REGISTROS8"/>' in xml, xml
    assert 'lib="7" loc="(560,200)" name="REGISTROS8"' not in xml, xml

    # ...while a builtin component with the same lib keeps it (non-subcircuit)
    builtin = Component(loc=(100, 100), name="Pin", lib="7")
    proj.circuits[-1].components.append(builtin)
    xml2 = dump(proj)
    assert '<comp lib="7" loc="(100,100)" name="Pin"' in xml2, xml2


def test_wire_l_path_helper_is_axis_aligned_only() -> None:
    """wire_l_path is THE sanctioned connection constructor: never diagonal."""
    from logisim_ita_mcp.circ.model import wire_l_path

    # Already aligned: single wire, unchanged
    assert [(w.start, w.end) for w in wire_l_path((0, 0), (10, 0))] == [((0, 0), (10, 0))]
    assert [(w.start, w.end) for w in wire_l_path((5, 5), (5, 9))] == [((5, 5), (5, 9))]

    # Diagonal intent: horizontal-then-vertical L through (end.x, start.y)
    segs = wire_l_path((560, 200), (1040, 0))
    assert [(w.start, w.end) for w in segs] == [
        ((560, 200), (1040, 200)),
        ((1040, 200), (1040, 0)),
    ]
    for w in segs:
        assert w.start[0] == w.end[0] or w.start[1] == w.end[1], w


def test_structural_checks_flag_diagonals_and_lib_violations() -> None:
    """structural_checks catches both load-killers without a JVM."""
    import tempfile

    from logisim_ita_mcp.circ.verifier import structural_checks

    bad = """<?xml version="1.0" encoding="UTF-8"?>
<project source="2.16.2.2.jar" version="1">
  <main name="main"/>
  <circuit name="REGISTROS8"/>
  <circuit name="main">
    <wire from="(250,110)" to="(280,140)"/>
    <wire from="(0,0)" to="(10,0)"/>
    <comp lib="7" loc="(560,200)" name="REGISTROS8"/>
  </circuit>
</project>
"""
    with tempfile.NamedTemporaryFile("w", suffix=".circ", delete=False) as fh:
        fh.write(bad)
        path = fh.name
    checks = structural_checks(path)
    assert checks["ok"] is False
    assert checks["diagonal_count"] == 1
    assert checks["diagonals"] == [{"from": "(250,110)", "to": "(280,140)"}]
    assert checks["subcircuit_lib_violations"] == [{"name": "REGISTROS8", "lib": "7"}]

    # A clean file passes
    good = bad.replace('<wire from="(250,110)" to="(280,140)"/>', "").replace(
        '<comp lib="7" loc="(560,200)" name="REGISTROS8"/>',
        '<comp loc="(560,200)" name="REGISTROS8"/>',
    )
    with tempfile.NamedTemporaryFile("w", suffix=".circ", delete=False) as fh:
        fh.write(good)
        path2 = fh.name
    assert structural_checks(path2)["ok"] is True
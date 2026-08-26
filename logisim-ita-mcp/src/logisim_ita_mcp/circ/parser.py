"""Parse a Logisim ITA .circ file into the model.

Adapted from virsi/logisim-mcp for Logisim ITA 2.16.x format.
Hardened against XXE and billion-laughs attacks.
"""

from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

from .model import Circuit, Component, Lib, Project, Wire, parse_loc

_KNOWN_PROJECT_CHILDREN = {"lib", "main", "circuit"}
_KNOWN_CIRCUIT_CHILDREN = {"a", "comp", "wire"}

MAX_CIRC_BYTES = 25 * 1024 * 1024

_DTD_OR_ENTITY = re.compile(rb"<!DOCTYPE|ENTITY\b", re.IGNORECASE)


def _check_no_dtd(data: bytes) -> None:
    if _DTD_OR_ENTITY.search(data):
        raise ValueError(
            "DOCTYPE / ENTITY declarations are not allowed in .circ files"
        )


def _make_parser() -> etree.XMLParser:
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        huge_tree=False,
    )


def _attrs_to_dict(el: etree._Element) -> dict[str, str]:
    out: dict[str, str] = {}
    for sub in el.iterchildren(tag="a"):
        name = sub.get("name")
        val = sub.get("val", "")
        if name is None:
            # Handle <a> with text content (e.g., ROM/RAM contents)
            if sub.text:
                out[name or ""] = sub.text.strip()
            continue
        # For ROM/RAM contents, val might be in text
        if not val and sub.text:
            val = sub.text.strip()
        out[name] = val
    return out


def _tostring(el: etree._Element) -> str:
    return etree.tostring(el, encoding="unicode")


def parse(path_or_xml: str | Path) -> Project:
    """Parse a .circ file or raw XML string into a Project."""
    parser = _make_parser()
    if isinstance(path_or_xml, Path) or (
        isinstance(path_or_xml, str)
        and "\n" not in path_or_xml
        and Path(path_or_xml).exists()
    ):
        p = Path(path_or_xml)
        size = p.stat().st_size
        if size > MAX_CIRC_BYTES:
            raise ValueError(f".circ file too large ({size} > {MAX_CIRC_BYTES})")
        data = p.read_bytes()
        _check_no_dtd(data)
        root = etree.fromstring(data, parser=parser)
    else:
        data = (
            path_or_xml.encode()
            if isinstance(path_or_xml, str)
            else path_or_xml
        )
        if len(data) > MAX_CIRC_BYTES:
            raise ValueError(f"XML input too large ({len(data)} > {MAX_CIRC_BYTES})")
        _check_no_dtd(data)
        root = etree.fromstring(data, parser=parser)

    if root.tag != "project":
        raise ValueError(f"expected <project> root, got <{root.tag}>")

    project = Project(
        source=root.get("source", "2.16.2.2"),
        version=root.get("version", "1.0"),
    )

    if root.text and root.text.strip():
        project.leading_text = root.text

    for child in root:
        tag = child.tag
        if tag is etree.Comment:
            continue
        if tag == "lib":
            project.libs.append(
                Lib(
                    id=child.get("name", ""),
                    desc=child.get("desc", ""),
                    tools_raw_xml=[_tostring(t) for t in child],
                )
            )
        elif tag == "main":
            project.main = child.get("name", project.main)
        elif tag == "circuit":
            project.circuits.append(_parse_circuit(child))
        else:
            project.extras_raw_xml.append(_tostring(child))

    return project


def _parse_circuit(el: etree._Element) -> Circuit:
    circuit = Circuit(name=el.get("name", ""))
    circuit.attrs = _attrs_to_dict(el)
    for child in el:
        tag = child.tag
        if tag is etree.Comment:
            continue
        if tag == "a":
            continue
        if tag == "comp":
            circuit.components.append(
                Component(
                    lib=child.get("lib", ""),
                    name=child.get("name", ""),
                    loc=parse_loc(child.get("loc", "(0,0)")),
                    attrs=_attrs_to_dict(child),
                )
            )
        elif tag == "wire":
            circuit.wires.append(
                Wire(
                    start=parse_loc(child.get("from", "(0,0)")),
                    end=parse_loc(child.get("to", "(0,0)")),
                )
            )
        else:
            circuit.extras_raw_xml.append(_tostring(child))

    return circuit
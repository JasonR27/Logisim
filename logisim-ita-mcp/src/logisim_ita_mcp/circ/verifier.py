"""Headless validation of .circ files against the Logisim ITA JAR.

The release jar at Compiled/Logisim-ITA.jar runs on Java 21 and supports
`-tty stats`, which loads the circuit headlessly and prints a component
histogram. Exit code / parse of the output proves a file loads without
hanging — the key guardrail before a user opens a generated file in the GUI.

Structural pre-checks (no JVM needed) catch the two known load-killers
BEFORE spending JVM time: diagonal wires (WireRepair.doOverlaps spins at
200%+ CPU / GB-scale heap) and subcircuit instances carrying a `lib`
attribute (modal "missing from library" dialog blocks the load).
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# The release jar the user actually runs (compatible with Java 21).
DEFAULT_ITA_JAR = Path(
    "/home/jasonr27/Documents/Github/JasonR27/Logisim/Compiled/Logisim-ITA.jar"
)

_WIRE_RE = re.compile(r'<wire from="\((-?\d+),(-?\d+)\)" to="\((-?\d+),(-?\d+)\)"')
_CIRCUIT_RE = re.compile(r'<circuit name="([^"]+)"')
_COMP_TAG_RE = re.compile(r"<comp\b[^>]*>")


def structural_checks(circ_path: str | Path) -> dict:
    """Static (no-JVM) checks for the known load-killers.

    Returns ``{ok, diagonal_count, diagonals, subcircuit_lib_violations,
    zero_length_wires}``. ``ok`` is True only when no diagonal wires exist
    and no subcircuit instance carries a ``lib`` attribute.
    """
    text = Path(circ_path).read_text(encoding="utf-8")

    diagonals: list[dict] = []
    zero_length = 0
    for x1, y1, x2, y2 in _WIRE_RE.findall(text):
        x1i, y1i, x2i, y2i = int(x1), int(y1), int(x2), int(y2)
        if x1i != x2i and y1i != y2i:
            diagonals.append({"from": f"({x1},{y1})", "to": f"({x2},{y2})"})
        elif (x1i, y1i) == (x2i, y2i):
            zero_length += 1

    circuit_names = set(_CIRCUIT_RE.findall(text))
    lib_violations: list[dict] = []
    for m in _COMP_TAG_RE.finditer(text):
        tag = m.group(0)
        name_m = re.search(r'\bname="([^"]+)"', tag)
        lib_m = re.search(r'\blib="([^"]*)"', tag)
        if name_m and lib_m and lib_m.group(1) and name_m.group(1) in circuit_names:
            lib_violations.append(
                {"name": name_m.group(1), "lib": lib_m.group(1)}
            )

    return {
        "ok": not diagonals and not lib_violations,
        "diagonal_count": len(diagonals),
        "diagonals": diagonals[:10],
        "subcircuit_lib_violations": lib_violations,
        "zero_length_wires": zero_length,
    }


class LogisimVerifier:
    """Runs headless `-tty stats` against the ITA jar."""

    def __init__(self, jar: Path | str = DEFAULT_ITA_JAR, timeout_s: int = 30) -> None:
        self.jar = Path(jar)
        self.timeout_s = timeout_s

    def verify_load(self, circ_path: str) -> dict:
        """Load a .circ headlessly. Returns {ok, source, component_histogram, error}."""
        cmd = [
            "java", "-jar", str(self.jar),
            "-tty", "stats", str(circ_path),
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout_s
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": f"TIMEOUT after {self.timeout_s}s — likely a hang/bad file",
                "component_histogram": {},
            }

        if proc.returncode != 0:
            return {
                "ok": False,
                "error": proc.stderr.strip() or proc.stdout.strip(),
                "component_histogram": {},
            }

        # Parse the histogram lines: " N\t N\tName   \tLib"
        histogram: dict[str, int] = {}
        lines = proc.stdout.splitlines()
        source = lines[0].strip() if lines else ""
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    histogram[parts[2].strip()] = int(parts[0].strip())
                except ValueError:
                    continue
        return {
            "ok": True,
            "source": source,
            "component_histogram": histogram,
        }


def verify(circ_path: str, jar: Path | str = DEFAULT_ITA_JAR) -> dict:
    """Convenience wrapper: structural checks + headless load in one result."""
    checks = structural_checks(circ_path)
    result = LogisimVerifier(jar).verify_load(circ_path)
    result["structural"] = checks
    # A file that fails structural checks is not safe to open even if the
    # headless -tty pass somehow completes.
    if not checks["ok"]:
        result["ok"] = False
        result.setdefault("error", "structural checks failed")
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python -m logisim_ita_mcp.circ.verifier <file.circ>")
        sys.exit(1)
    print(json.dumps(LogisimVerifier().verify_load(sys.argv[1]), indent=2))
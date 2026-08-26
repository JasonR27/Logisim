"""Headless validation of .circ files against the Logisim ITA JAR.

The release jar at Compiled/Logisim-ITA.jar runs on Java 21 and supports
`-tty stats`, which loads the circuit headlessly and prints a component
histogram. Exit code / parse of the output proves a file loads without
hanging — the key guardrail before a user opens a generated file in the GUI.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

# The release jar the user actually runs (compatible with Java 21).
DEFAULT_ITA_JAR = Path(
    "/home/jasonr27/Documents/Github/JasonR27/Logisim/Compiled/Logisim-ITA.jar"
)


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
    """Convenience wrapper returning a JSON-serializable result."""
    result = LogisimVerifier(jar).verify(circ_path)
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python -m logisim_ita_mcp.circ.verifier <file.circ>")
        sys.exit(1)
    print(json.dumps(LogisimVerifier().verify_load(sys.argv[1]), indent=2))
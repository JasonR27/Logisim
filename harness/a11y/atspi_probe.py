#!/usr/bin/env python3
"""AT-SPI probe: list apps, dump Logisim menu tree, invoke a named action.
Usage: atspi_probe.py [list|menus|invoke <action-substring>]
Requires: AT_SPI_BUS_ADDRESS set (at-spi bus running), Logisim+bridge running.
"""
import sys

import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi


def desktop():
    Atspi.init()
    return Atspi.get_desktop(0)


def walk(node, depth=0, out=None, maxdepth=6):
    if out is None:
        out = []
    if depth > maxdepth:
        return out
    try:
        name = node.get_name() or ""
        role = node.get_role_name() or ""
    except Exception:
        return out
    out.append(("  " * depth, role, name))
    try:
        n = node.get_child_count()
    except Exception:
        return out
    for i in range(min(n, 40)):
        try:
            walk(node.get_child_at_index(i), depth + 1, out, maxdepth)
        except Exception:
            pass
    return out


def find(node, pred, depth=0, maxdepth=12):
    try:
        if pred(node):
            return node
    except Exception:
        return None
    if depth >= maxdepth:
        return None
    try:
        n = node.get_child_count()
    except Exception:
        return None
    for i in range(min(n, 60)):
        try:
            hit = find(node.get_child_at_index(i), pred, depth + 1, maxdepth)
            if hit is not None:
                return hit
        except Exception:
            pass
    return None


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    d = desktop()
    if cmd == "list":
        for i in range(d.get_child_count()):
            try:
                a = d.get_child_at_index(i)
                print(f"app: {a.get_name()}")
            except Exception as e:
                print(f"app?: {e}")
    elif cmd == "menus":
        app = find(d, lambda n: "ogisim" in (n.get_name() or ""))
        if app is None:
            print("NO-LOGISIM-APP")
            return
        print(f"app: {app.get_name()}")
        for line in walk(app, maxdepth=4)[:80]:
            print(f"{line[0]}{line[1]}: {line[2]}")
    elif cmd == "children":
        want = sys.argv[2].lower()
        app = find(d, lambda n: "ogisim" in (n.get_name() or ""))
        node = find(app, lambda n: want == (n.get_name() or "").lower())
        if node is None:
            print(f"NO-NODE[{want}]")
            return
        try:
            n = node.get_child_count()
        except Exception as e:
            print(f"COUNT-ERR: {e}")
            return
        print(f"node role={node.get_role_name()} children={n}")
        for i in range(min(n, 40)):
            try:
                c = node.get_child_at_index(i)
                states = []
                try:
                    st = c.get_state_set()
                    states = [s for s in ("enabled", "visible", "showing", "sensitive") if st.contains(s)]
                except Exception:
                    pass
                nactions = 0
                try:
                    nactions = c.get_n_actions()
                except Exception:
                    pass
                print(f"  [{i}] {c.get_role_name()}: {c.get_name()} states={states} actions={nactions}")
            except Exception as e:
                print(f"  [{i}] ERR {e}")
    elif cmd == "invoke":
        want = sys.argv[2].lower()
        app = find(d, lambda n: "ogisim" in (n.get_name() or ""))
        if app is None:
            print("NO-LOGISIM-APP")
            return
        target = find(app, lambda n: want in (n.get_name() or "").lower())
        if target is None:
            print(f"NO-ACTION[{want}]")
            return
        try:
            n = target.get_n_actions()
            print(f"actions: {[target.get_action_name(i) for i in range(n)]}")
            ok = target.do_action(0)
            print(f"INVOKE[{want}] -> {ok}")
        except Exception as e:
            print(f"INVOKE-ERR[{want}]: {e}")


main()

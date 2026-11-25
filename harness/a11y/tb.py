#!/usr/bin/env python3
"""AT-SPI toolbar dump + click a tool button. Usage: tb.py [click <substr>]"""
import sys

import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi

Atspi.init()
d = Atspi.get_desktop(0)


def find(n, pred, depth=0):
    try:
        if pred(n):
            return n
    except Exception:
        return None
    if depth > 16:
        return None
    try:
        cnt = n.get_child_count()
    except Exception:
        return None
    for i in range(min(cnt, 100)):
        try:
            h = find(n.get_child_at_index(i), pred, depth + 1)
            if h is not None:
                return h
        except Exception:
            pass
    return None


def walk(n, depth=0, out=None):
    if out is None:
        out = []
    try:
        out.append(("  " * depth, n.get_role_name(), n.get_name() or ""))
    except Exception:
        return out
    if depth > 2:
        return out
    try:
        cnt = n.get_child_count()
    except Exception:
        return out
    for i in range(min(cnt, 40)):
        try:
            walk(n.get_child_at_index(i), depth + 1, out)
        except Exception:
            pass
    return out


app = find(d, lambda n: "ogisim" in (n.get_name() or ""))
tb = find(app, lambda n: (n.get_role_name() or "") == "tool bar")
if tb is None:
    print("NO-TOOLBAR")
    sys.exit(0)
if len(sys.argv) > 2 and sys.argv[1] == "click":
    want = sys.argv[2].lower()
    t = find(tb, lambda n: want in (n.get_name() or "").lower())
    if t is None:
        print(f"NO-BUTTON[{want}]")
    else:
        print(f"click[{t.get_name()}] ->", t.do_action(0))
else:
    for line in walk(tb)[:24]:
        print(f"{line[0]}{line[1]}: {line[2]}")

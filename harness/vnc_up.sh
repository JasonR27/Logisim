#!/usr/bin/env bash
# vnc_up.sh — deterministic VNC-capable startup (run INSIDE logisim-vnc).
# Order: Xvfb -> openbox -> x11vnc (all interfaces) -> app. All persist.
set -euo pipefail
CIRC="${1:-/workspace/circ.circ}"
pkill -x Xvfb 2>/dev/null || true
pkill -x x11vnc 2>/dev/null || true
pkill -x java 2>/dev/null || true
sleep 2
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
sleep 2
openbox --sm-disable &
sleep 2
nohup x11vnc -display :99 -nopw -rfbport 5900 -shared -forever -bg -o /tmp/x11vnc.log >/dev/null 2>&1
sleep 3
nohup java -jar /opt/logisim/Logisim-ITA.jar "$CIRC" >/tmp/app.log 2>&1 &
sleep 18
echo "vnc_up done: $(pgrep -c -x x11vnc) x11vnc, $(pgrep -c -x java) java"

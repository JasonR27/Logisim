#!/usr/bin/env bash
# harness_ctl.sh — long-running Logisim ITA control plane (WM-managed Xvfb).
# Usage: harness_ctl.sh up <circ> | shot <out.png> | tick [n] | toggle | reset
#        | key <keys...> | click <x> <y> | zoomin [n] | zoomout [n] | status | down
# Env: HARNESS_NAME (default logisim-ctl), HARNESS_IMG, WS_DIR, OUT_DIR.
set -euo pipefail
NAME="${HARNESS_NAME:-logisim-ctl}"
IMG="${HARNESS_IMG:-logisim-gui-harness:latest}"
WS="${WS_DIR:-/tmp/opencode/ctl_ws}"
OUT="${OUT_DIR:-/tmp/opencode/ctl_out}"
D="DISPLAY=:99"

die() { echo "ctl: ERROR $*" >&2; exit 1; }
ex() { docker exec "$NAME" bash -c "export $D; $*" ; }

cmd="${1:-status}"
case "$cmd" in
  up)
    CIRC="${2:-/workspace/circ.circ}"
    mkdir -p "$WS" "$OUT"
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    docker run -d --name "$NAME" --entrypoint /bin/bash \
      -v "$WS:/workspace:ro" -v "$OUT:/out" "$IMG" \
      -c "Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp & sleep 2; export DISPLAY=:99; openbox --sm-disable & sleep 2; java -jar /opt/logisim/Logisim-ITA.jar $CIRC & sleep infinity" >/dev/null
    sleep 22
    ex "xdotool search --name 'Logisim' | head -3"
    ;;
  shot)
    OUTP="${2:-/out/shot.png}"; N="${3:-1}"
    for _ in $(seq 1 "$N"); do
      ex "xwd -root -display :99 -silent -out /tmp/ctl.xwd && convert xwd:/tmp/ctl.xwd $OUTP"
      sleep 1
    done
    ;;
  tick)  # single-step clock N times (default 1), 2s apart
    N="${2:-1}"
    for _ in $(seq 1 "$N"); do ex "xdotool key ctrl+t"; sleep 2; done
    ;;
  toggle)  # ticks on/off
    ex "xdotool key ctrl+k"; sleep 1 ;;
  reset)  # simulation reset
    ex "xdotool key ctrl+r"; sleep 2 ;;
  key)
    shift; ex "xdotool key $*"; sleep 1 ;;
  click)
    ex "xdotool mousemove $2 $3 click 1"; sleep 1 ;;
  zoomin|zoomout)
    K="plus"; [ "$cmd" = "zoomout" ] && K="minus"
    N="${2:-3}"
    for _ in $(seq 1 "$N"); do ex "xdotool key ctrl+$K"; sleep 1; done
    ;;
  windows)
    ex "xdotool search --name 'Logisim'; echo ---; xdotool getwindowfocus" ;;
  status)
    docker ps --filter "name=$NAME" --format "{{.Names}} {{.Status}}" | grep -q . || die "$NAME not running (use: up)"
    ex "ps aux | grep -c '[L]ogisim-ITA'" ;;
  down)
    docker rm -f "$NAME" >/dev/null 2>&1 || true; echo "ctl: $NAME stopped" ;;
  *) die "unknown: $cmd" ;;
esac

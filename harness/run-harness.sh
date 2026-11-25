#!/usr/bin/env bash
# Runs Logisim ITA under in-container Xvfb and captures a PNG screenshot
# of the MAIN editor frame (polls until the splash screen is gone).
set -euo pipefail

CIRC="${1:-/workspace/regenerated_fixed.circ}"
OUT_DIR="/out"
SHOT="${OUT_DIR}/logisim_shot.png"
MAX_WAIT="${MAX_WAIT_SECONDS:-90}"
SCREEN="${SCREEN_GEOMETRY:-1920x1080x24}"

mkdir -p "${OUT_DIR}"
echo "[harness] $(date -Iseconds) start, circuit=${CIRC}, screen=${SCREEN}" | tee -a "${OUT_DIR}/harness.log"

# 1. Virtual display — fully in-container, deterministic geometry
Xvfb :99 -screen 0 "${SCREEN}" -nolisten tcp &
XVFB_PID=$!
sleep 2
export DISPLAY=:99

# 2. Launch Logisim ITA with the circuit open at startup (HOW_TO_START.md §A.3)
java -jar /opt/logisim/Logisim-ITA.jar "${CIRC}" &
LOGISIM_PID=$!

# 3. Poll: the splash screen has an animated progress bar and sits on top
#    of the main frame until the circuit finishes loading. While it is
#    visible, consecutive captures differ; once gone, the editor paints a
#    static frame. So: capture every 3s, stop at the first pair of
#    identical consecutive captures.
prev="/tmp/prev.png"
rm -f "${prev}" /tmp/poll.png
stable_required=2
stable=0
elapsed=0
while [ "${elapsed}" -lt "${MAX_WAIT}" ]; do
    sleep 3
    elapsed=$((elapsed + 3))
    xwd -root -display :99 -silent -out /tmp/shot.xwd 2>/dev/null
    convert xwd:/tmp/shot.xwd /tmp/poll.png
    if [ -f "${prev}" ] && cmp -s /tmp/poll.png "${prev}"; then
        stable=$((stable + 1))
        if [ "${stable}" -ge "${stable_required}" ]; then
            cp /tmp/poll.png "${SHOT}"
            echo "[harness] display stabilized at ~${elapsed}s" | tee -a "${OUT_DIR}/harness.log"
            break
        fi
    else
        stable=0
    fi
    cp /tmp/poll.png "${prev}"
done
if [ ! -f "${SHOT}" ]; then
    echo "[harness] WARN: stabilization window expired, using last capture" | tee -a "${OUT_DIR}/harness.log"
    cp /tmp/poll.png "${SHOT}"
fi
identify "${SHOT}" | tee -a "${OUT_DIR}/harness.log"

# 5. Teardown
kill "${LOGISIM_PID}" "${XVFB_PID}" 2>/dev/null || true
wait 2>/dev/null || true

echo "[harness] $(date -Iseconds) screenshot written to ${SHOT}" | tee -a "${OUT_DIR}/harness.log"

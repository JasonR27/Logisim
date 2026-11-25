#!/usr/bin/env bash
# a11y_up.sh — deterministic AT-SPI stack startup inside logisim-a11y.
# Order: session dbus -> at-spi bus -> Xvfb -> java+bridge. All persist (nohup).
set -euo pipefail
CIRC="${1:-/workspace/circ.circ}"
export XDG_RUNTIME_DIR=/tmp/rt-a11y
mkdir -p "$XDG_RUNTIME_DIR"
pkill -x java 2>/dev/null || true
pkill -x Xvfb 2>/dev/null || true
sleep 2
dbus-daemon --session --fork --print-address > /tmp/dbus.addr 2>/dev/null
export DBUS_SESSION_BUS_ADDRESS=$(cat /tmp/dbus.addr)
export DISPLAY=:99
nohup /usr/libexec/at-spi-bus-launcher --launch-immediately >/tmp/bus.log 2>&1 &
sleep 5
export AT_SPI_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/at-spi/bus_99"
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp & sleep 2
CP=/opt/logisim/Logisim-ITA.jar:/opt/a11y/java-a11y-bridge-0.1.0-SNAPSHOT.jar:/opt/a11y/dbus-java-core-5.2.0.jar:/opt/a11y/dbus-java-transport-native-unixsocket-5.2.0.jar:/opt/a11y/slf4j-api-2.0.17.jar
nohup java -cp $CP -Djavax.accessibility.assistive_technologies=org.a11y.bridge.A11yBridge \
  com.cburch.logisim.Main "$CIRC" >/tmp/logisim-a11y.log 2>&1 &
sleep 22
grep -c "registered with AT-SPI2 registry" /tmp/logisim-a11y.log

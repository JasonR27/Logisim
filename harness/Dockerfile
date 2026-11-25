# PROPOSAL — not yet built. Awaiting user approval per plan T2.5.
FROM eclipse-temurin:21-jre-jammy

ENV DEBIAN_FRONTEND=noninteractive

# Xvfb (virtual display), x11-apps (xwd), ImageMagick (xwd->png), openbox (WM:
# focus/activation/EWMH so xdotool window ops + key delivery are reliable),
# X11 client libs REQUIRED by libawt_xawt.so (libXi/libXext/libXrender/libXtst),
# fontconfig + DejaVu fonts (AWT/Swing text rendering), procps (ps for health)
RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb \
        x11-apps \
        imagemagick \
        xdotool \
        openbox \
        x11vnc \
        libxi6 \
        libxext6 \
        libxrender1 \
        libxtst6 \
        libfontconfig1 \
        fonts-dejavu-core \
        procps \
        at-spi2-core \
        gir1.2-atspi-2.0 \
        python3-gi \
        python3-pip \
        dbus \
    && rm -rf /var/lib/apt/lists/*

# AT-SPI Java bridge (pure Java, JDK21): exposes Swing tree over AT-SPI2 D-Bus
# so dogtail/pyatspi can invoke named actions (Simulate->Step/Reset/Tick).
COPY harness/a11y/java-a11y-bridge/bridge/target/java-a11y-bridge-0.1.0-SNAPSHOT.jar /opt/a11y/
COPY harness/a11y/java-a11y-bridge/bridge/target/lib/dbus-java-core-5.2.0.jar /opt/a11y/
COPY harness/a11y/java-a11y-bridge/bridge/target/lib/dbus-java-transport-native-unixsocket-5.2.0.jar /opt/a11y/
COPY harness/a11y/java-a11y-bridge/bridge/target/lib/slf4j-api-2.0.17.jar /opt/a11y/

# Logisim ITA jar — Java-21-compatible build (Compiled/, NOT target/)
COPY Compiled/Logisim-ITA.jar /opt/logisim/Logisim-ITA.jar

COPY harness/run-harness.sh /usr/local/bin/run-harness.sh
COPY harness/harness_ctl.sh /usr/local/bin/harness_ctl.sh
RUN chmod +x /usr/local/bin/run-harness.sh /usr/local/bin/harness_ctl.sh

# /workspace: .circ input (mount read-only)  /out: screenshot + log
VOLUME ["/workspace", "/out"]

ENTRYPOINT ["run-harness.sh"]
CMD ["/workspace/regenerated_fixed.circ"]

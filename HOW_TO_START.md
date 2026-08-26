# How to Start the Logisim ITA App

**Repo:** `/home/jasonr27/Documents/Github/JasonR27/Logisim`
**Project:** Logisim ITA (Italian fork of Logisim, a digital-circuit simulator)

This guide shows every way to launch the app: running a pre-built JAR, building from source with Maven, and launching from an IDE. It also includes troubleshooting for this specific machine.

---

## 1. High-Level Overview

| Item | Value |
|------|-------|
| Main class | `com.cburch.logisim.Main` |
| Maven module | `Logisim-Fork` (a Maven project inside the repo) |
| Java compiler level | JDK 8 (source/target = 8) |
| Your Java runtime | OpenJDK 21.0.12.1 |
| Your Maven version | Maven 3.9.9 |
| GUI display | Linux X11, `DISPLAY=:1` (available) |
| Sample circuits | `projects/*.circ` |
| Pre-built artifacts | `Compiled/Logisim-ITA.jar` and `Logisim-Fork/target/` outputs |

> **Quickest start (no rebuild needed):**
> ```bash
> java -jar /home/jasonr27/Documents/Github/JasonR27/Logisim/Compiled/Logisim-ITA.jar
> ```
> If you prefer the artifact produced by the Maven build, use
> `/home/jasonr27/Documents/Github/JasonR27/Logisim/Logisim-Fork/target/Logisim-jar-with-dependencies.jar`
> instead — see below.

---

## 2. Option A — Run a Pre-Built JAR (fastest, no compilation)

The repo already contains ready-to-run JARs, so you don't need Maven at all unless you changed the source.

### A.1. The pre-compiled release JAR
```bash
cd /home/jasonr27/Documents/Github/JasonR27/Logisim
java -jar Compiled/Logisim-ITA.jar
```

### A.2. The JAR that was produced by `mvn package`
```bash
java -jar Logisim-Fork/target/Logisim-jar-with-dependencies.jar
```

This is the "fat" JAR (all dependencies bundled). Its manifest declares `Main-Class: com.cburch.logisim.Main`, so `java -jar` works with no extra classpath.

### A.3. Open a circuit you have in the repo
Pass a `.circ` file on the command line to open it directly at startup:
```bash
java -jar Logisim-Fork/target/Logisim-jar-with-dependencies.jar \
  "/home/jasonr27/Documents/Github/JasonR27/Logisim/projects/lab miercoles.circ"
```

Circuits available under `projects/`:
- `cpu tuanis for LOAD, LOADI and STORE, STOREI.circ`
- `cpu tuanis q si tiene registros de propósito general.circ`
- `lab miercoles.circ`

### A.4. Background / detached launch
```bash
nohup java -jar Compiled/Logisim-ITA.jar > /tmp/logisim.log 2>&1 &   echo "pid $!"
```

---

## 3. Option B — Build from Source with Maven

### B.1. Build the full package
```bash
cd /home/jasonr27/Documents/Github/JasonR27/Logisim/Logisim-Fork
mvn package
```
On success the main artifact is `target/Logisim-jar-with-dependencies.jar` (this already exists on your machine, so you can skip rebuilding).

### B.2. If you only want the JAR (skip the Windows `.exe`)
The pom attaches a `launch4j` plugin that generates a Windows `Logisim-ITA.exe` during the `package` phase. On Linux this can fail or pull in extra tooling. To build only the jar:

```bash
mvn clean package -Dlaunch4j.skip=true   # not all launch4j versions honor this flag
```

If the flag is ignored, build the jar directly through the assembly plugin so only the `jar-with-dependencies` is produced:

```bash
mvn clean compile
mvn assembly:single
```
Then run:
```bash
java -jar target/Logisim-jar-with-dependencies.jar
```

> **Tip:** Your `target/` already contains a good `Logisim-jar-with-dependencies.jar`, so for quick iterations just run that JAR. Only re-run `mvn package` (or `mvn clean package`) when you change source under `src/main/java`.

---

## 4. Option C — Run from an IDE

The repo ships as a Maven project (also valid Eclipse project, see `.project` / `.classpath`).

1. Open IntelliJ IDEA or Eclipse and use **File → Open** / **Import**.
2. Pick the folder `Logisim-Fork` (contains `pom.xml`).
3. Let the IDE import it as a **Maven project** (it will download the deps: `javahelp`, `mrjadapter`, `fontchooser`).
4. Create a Run Configuration:
   - Main class: `com.cburch.logisim.Main`
   - Working directory: `Logisim-Fork`
   - JRE: any 8+ (OpenJDK 21 is fine as long as it's used to compile to target 8)
5. Click **Run**. The Logisim GUI window opens.

Note: this pom compiles to **Java 8** even though your default JDK is 21; the compiler `--release 8` setting is handled by the plugin, so no extra `rt.jar` / bootclasspath tricks are needed.

---

## 5. Recommended Setup (if you will work on this machine often)

Create a small launcher that prefers the local build over the release JAR:

```bash
#!/usr/bin/env bash
# start-logisim.sh
set -e
DIR="/home/jasonr27/Documents/Github/JasonR27/Logisim"
LOCAL="$DIR/Logisim-Fork/target/Logisim-jar-with-dependencies.jar"
RELEASE="$DIR/Compiled/Logisim-ITA.jar"
JAR="$LOCAL"
[ -f "$JAR" ] || JAR="$RELEASE"
exec java -jar "$JAR" "$@"
```

Make it executable: `chmod +x start-logisim.sh`
Run: `./start-logisim.sh "projects/lab miercoles.circ"`

---

## 6. Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `java.lang.UnsupportedClassVersionError` | JAR compiled for a newer Java than your JRE. Install JDK 8+ (you have 21 — fine). |
| Blank window / error at startup, `DISPLAY` unset | GUI needs an X server. Launch inside a desktop session where `echo $DISPLAY` prints e.g. `:1`. On this machine `DISPLAY=:1` is already set. |
| `java.awt.HeadlessException` | No display available. Use `ssh -X` or re-run inside the desktop GUI session. |
| Maven fails on the launch4j `.exe` step | See §3.2 — skip `.exe` generation and run only the jar via `mvn assembly:single`. |
| Could not find/load main class | Use `Logisim-jar-with-dependencies.jar` (deps bundled), not the thin `Logisim.jar`. |
| Blue/red random lines, high-freq glitches | Known Logisim rendering bug (README §Bugs). Cosmetic; ignore. |
| `.circ` file won't open | Paths with spaces need quotes: `java -jar ... "projects/lab miercoles.circ"`. |

---

## 7. Verification Checklist

After a launch, confirm:
1. A **Logisim ITA window** (toolbar + canvas) appears.
2. **File → Open** works; open a file from `projects/`.
3. You can place gates (e.g. Wiring → Programmable Generator, TTL 74xx) and wire them.
4. Use **Analyze Circuit** to see the truth table / expression.

If anything fails, capture the console output (`java -jar ...` prints to the terminal) and refer to the troubleshooting table.

---

## 8. Reference

- Maven module: `Logisim-Fork/pom.xml` (`finalName=Logisim`, `packaging=jar`)
- Entry point: `Logisim-Fork/src/main/java/com/cburch/logisim/Main.java`
- Manifest: `Logisim-Fork/src/main/java/resources/META-INF/MANIFEST.MF` → `Main-Class: com.cburch.logisim.Main`
- Project version: `version.xml` → `2.16.2.2`
- Website / changelog: https://logisim.altervista.org

---

You now have three working ways to start the app (pre-built jar, Maven build, or IDE) plus a troubleshooting guide tailored to this machine.
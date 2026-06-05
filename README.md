# tekscan-connector

**Reading a real force sensor into Claude Code on Linux — with no vendor API, no SDK, no Linux support, and no community solution. Reverse-engineered from scratch.**

A proof-of-concept that an AI coding agent (Claude Code) can take action in the physical world by connecting *directly* to a sensor, decoding its protocol, and reading live inputs — even when the manufacturer ships **nothing** for your platform.

The sensor: a **Tekscan FlexiForce ELF System** (a thin-film FlexiForce force sensor on a USB "handle"). Officially it's **Windows-only**, with no public API/SDK, no Linux driver, and no prior open reverse-engineering. Starting from a few photos of the box, the sensor, and the USB stick, this project recovers the wire protocol and streams live force into the browser on Linux.

> ⚖️ **No proprietary software is included in this repo.** The Tekscan installer, `ElfMPort.exe`, vendor DLLs, and all decompilation output are deliberately git-ignored. What's published here is *our own code* and the *protocol facts* we derived.

---

## The result

A zero-install (Python-stdlib) **web GUI** that streams live force at ~10 Hz, with a strip chart and 2-point calibration — running on Linux, no Windows, no Wine, no vendor SDK:

```bash
python probe/gui_web.py   # → open http://localhost:8777, press the sensor, watch it move
```

## The decoded protocol (the hard-won facts)

| Property | Value |
|---|---|
| Hardware | FTDI **FT232R**, USB **VID 0x11DA / PID 0x0012** |
| Linux access | `pyftdi`/`libusb` (kernel `ftdi_sio` ignores 0x11DA); `uaccess` udev rule |
| **Baud** | **1,000,000** (the single biggest gotcha — the decompiled constant was misleading) |
| Init | CBUS3 reset pulse → 1 Mbaud → 8N1 → drop to UART mode to read |
| **Start streaming** | `SetReferenceVoltage(0x32, Vref)` → `SetFrameRate(0x39, …)` → `StartRecording(0x3d)` |
| Frame | one byte per frame = 8-bit force count (no-load LOW, rises with force) |

The device is a **free-running streaming** sensor (not poll/response): once `StartRecording` is sent it pushes one force byte per frame continuously. Full write-up in [`re/FINDINGS.md`](re/FINDINGS.md).

## Repository layout

```
tekscan_connector/   clean Linux driver — protocol.py (init + wire), calibration.py
probe/               probe scripts + gui_web.py (the live web GUI) + triallog.py
re/FINDINGS.md       the decoded protocol, with evidence
re/scripts/*.java    our headless-Ghidra decompilation driver scripts
problem_statement.md / OVERNIGHT_GOAL.md   the reverse-engineering plan & log
udev/                the uaccess udev rule for non-root USB access
gelsight_*.md / .pdf GelSight follow-on research (see below)
```

*Deliberately excluded from the public repo (see `.gitignore`):* the proprietary `vendor/` payload, the Ghidra/JDK toolchain and decompiled C (`re/ghidra`, `re/jdk21`, `re/project`, `re/logs`), ML weights (`sam_assets`), the video-build working dir (`meta/`), and all large media (`*.mp4`).

## Companion skills (Claude Code)

Two global skills automate the rig:
- **`tekscan-launch-protocol`** — plays the assembly video, prints the connect steps, and starts the live GUI.
- **`tekscan-measurement-history`** — captures a force measurement, saves the data file + a strip-chart plot to disk.

## What's next: GelSight

The Tekscan crack was the *hard* case (nothing official). The follow-on research asks whether the **GelSight** tactile-sensor family is easier — see [`gelsight_preliminary_product_research.md`](gelsight_preliminary_product_research.md) and the PDFs. Short answer: the **GelSight Mini** is the *opposite* of Tekscan (open Python SDK, Linux-native, plug-and-play), while the bigger units are the same Windows/paid wall — and **nobody ships an MCP or a Claude-native interface yet**, which is open territory.

---

*Built with [Claude Code](https://claude.com/claude-code) on Pop!_OS. The thesis: an AI agent that connects to the physical world through sensors, starting from nothing but photos and curiosity.*

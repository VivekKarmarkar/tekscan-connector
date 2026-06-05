# GelSight — Preliminary Product Research
### Can Claude Code talk to a GelSight tactile sensor on Linux — out of the box, or do we reverse-engineer it like we did Tekscan?

**Date:** 2026-06-04 · **Context:** Our Tekscan ELF proof-of-concept showed Claude can connect to a real-world force sensor on Linux **with literally nada** — no API, no SDK, no Linux driver, no community solution — just a few photos of the box/sensor/USB and a from-scratch reverse-engineering of the byte protocol. The question now: does the **GelSight** family of tactile sensors extend that idea, and is it *easier* (official support) or do we run the same "crack it ourselves" playbook?

> **TL;DR — GelSight is split in two.** One product (the **GelSight Mini**, ~$510) is the *opposite* of Tekscan: a fully **open-source Python SDK, GPL-3.0, Linux-native, plug-and-play over USB** — essentially a one-session integration. The rest of the line (**GelSight Mobile, Max, Modulus**) is the *same wall* as Tekscan: **Windows-only GUIs**, programmatic access only via **paid, license-gated** APIs. **No product has an MCP server or any Claude/LLM-agent-native integration.**

---

## 1) Official API / SDK for all their sensors? Official MCP?

**Partly — and only the Mini's is free/open. There is NO official MCP server for anything.**

| Offering (github.com/gelsightinc) | For which sensor | Language | License / cost | Notes |
|---|---|---|---|---|
| **`gsrobotics`** | **GelSight Mini** (+ legacy R1.5) | **Python** | **GPL-3.0, free, public** (~189★, active) | The only free, Linux-friendly SDK. Live tactile stream, NN depth + 3D point cloud, marker/shear tracking → `.npy`/`.csv`. |
| **GelSight Mobile Async API** (`apidemo`) | GelSight **Mobile** (industrial) | .NET DLL (C# demo) | **Paid / gated** — "requires a licensed GelSight Mobile installed" (Mobile 3.8+) | Must enable an API server in the Windows GUI. Windows 11 only. |
| **`GelSightSDK`** (`sdkdemo`) | GelSight systems → 3D heightmaps | **C++** | **Paid / gated** — "requires a valid license for GelSightSdk" | Supports Windows **and** Linux, but license-locked. |
| `gsmatlab`, `tactiledemo` | helpers / batch | MATLAB / — | — | Supporting repos. |

- **MCP (Model Context Protocol): CONFIRMED NONE.** No GelSight MCP server exists in the official MCP registry, on GitHub, or anywhere indexed. GelSight has **zero** MCP presence.

## 2) Official software for Linux — for all their sensors?

**No — only the Mini. Everything else is Windows-only.**

- ✅ **GelSight Mini → Linux-native.** `gsrobotics` README has a dedicated **Linux/Ubuntu install** section (Python 3.12 + `v4l-utils`). The Mini enumerates as a **standard USB UVC webcam** — "detected like a webcam, so there is no need to install software to get started." On Linux it's a plain `/dev/videoN` v4l2 device; `cv2.VideoCapture` reads it directly. **ROS/ROS2 (Humble) integrations exist.** All "tactile" depth is software reconstruction on top of raw camera frames.
- ❌ **GelSight Mobile / Max / Modulus / Shock-Protected → Windows-only GUI.** The Mobile app needs Windows 10+; the Async API explicitly needs **Windows 11** (Win10 support ends Oct 14 2025). No Linux build of the consumer/metrology GUI. (The paid C++ `GelSightSDK` library does run on Linux, but that's the licensed library, not the app.)

## 3) AI-agent-native compatibility, focused on Claude Code?

**None — for any product.** No MCP server, no LLM/agent hooks, no natural-language control, no Claude integration anywhere. GelSight's marketing phrase *"AI-Enhanced Metrology Software"* refers strictly to **computer-vision defect detection/classification** on surface scans — the announcement never mentions LLMs, agents, MCP, or chatbots. Partner stories are **OEM embedding** (e.g., Cadre Forensics putting a GelSight sensor in a firearms imager), not agentic.

> **The only realistic agent path today is DIY:** wrap the open GPL-3.0 `gsrobotics` Python SDK on a **GelSight Mini** and expose it to Claude Code yourself.

---

## What this means for us (Tekscan → GelSight)

| | **Tekscan ELF** (what we did) | **GelSight Mini** (easy path) | **GelSight Mobile/Max/Modulus** (hard path) |
|---|---|---|---|
| Linux support | ❌ none (Windows-only) | ✅ native (Python, v4l2, ROS2) | ❌ Windows-only GUI |
| API / SDK | ❌ none — RE'd the FTDI byte protocol | ✅ open Python SDK (GPL-3.0, free) | ⚠️ paid, license-gated (.NET / C++) |
| Connection | FTDI USB, unknown protocol (we cracked 1 Mbaud + `SetFrameRate`→`StartRecording`) | USB **UVC webcam** — `cv2.VideoCapture`, **zero RE** | locked GUI / paid API |
| Effort for a Claude-Code read-loop | **multi-week reverse-engineering** | **a single session** (pip install, list /dev/video, read frames) | contact-sales + Windows |
| MCP / Claude-native | ❌ | ❌ (DIY wrap) | ❌ |

**Bottom line:** If we want *easy*, the **GelSight Mini** is essentially plug-and-play on Linux — we'd skip the whole reverse-engineering odyssey. If we go for the bigger, phone-sized **Mobile/Max** units, we're back in **exactly the Tekscan situation** (closed, Windows, paid) — and our proof-of-concept already showed that **we can still crack it from nothing** if we have to. Either way, **nobody ships an MCP or a Claude-native tactile sensor yet** — that's open territory we could build into.

---

### Sources
GitHub: `gelsightinc/gsrobotics` (+ `/blob/main/README.md`), `gelsightinc/apidemo`, `gelsightinc/sdkdemo`. Web: gelsight.com/products, /gelsightmini, /product/gelsight-max, /product/gelsight-mobile, the "AI-Enhanced Metrology Software" press release. Community: `joehjhuang/gs_sdk`, `duyipai/gsmini`, `RVSATHU/gelsight_mini_ros`.

*See [`gelsight_price_point_analysis.md`](gelsight_price_point_analysis.md) for form-factor & pricing.*

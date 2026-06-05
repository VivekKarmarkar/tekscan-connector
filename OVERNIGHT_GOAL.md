# Overnight Goal — crack the Tekscan FlexiForce ELF live-read on Linux

**Author:** Claude (self-authored problem statement for autonomous overnight work)
**Written:** 2026-06-04, ~01:35 local, while Vivek sleeps (power kept on, no reboot).
**One-line mission:** Read the live force value off the genuine Tekscan ELF handle on Linux, no Windows, no Wine. Everything is solved except identifying the exact byte that reads the live sensor — and that is now a *device-free static reverse-engineering* problem I can grind on all night.

---

## 0. How to read this document

This is written so that **a fresh agent with zero conversation context can resume the work cold.** It states what is already proven (so I never re-derive it), the single remaining gap, the exact toolchain (now persistent — survives a crash), the overnight method, the success criteria, and the morning capstone that needs Vivek.

Authoritative state lives in three places:
1. **This file** — the plan and the running scoreboard (§7).
2. **Memory** — `~/.claude/projects/-home-vivekkarmarkar-Python-Files-tekscan-connector/memory/tekscan-elf-research-facts.md` (the decoded protocol facts) and `tekscan-connector-goal.md` (the why).
3. **`re/logs/`** — every Ghidra decompilation pass.

---

## 1. Mission & hard constraints

- **Goal:** plug the handle in → live force in Claude Code. Plug-n-play. Calibration handled in software, never a manual burden on Vivek.
- **Platform:** Linux (Pop!_OS). **NO Windows machine exists. Wine is vetoed** ("hacky"). The solution must be Linux-native.
- **Hardware on hand:** the ELF USB handle + FlexiForce sensor (inserted) + OIML M1 weight set (10/20/20/50/100/100/200/500 g = 1000 g total).

## 2. What is ALREADY SOLVED — do NOT re-derive

| Thing | Status | Where |
|---|---|---|
| Hardware identity | FTDI **FT232R**, USB **VID 0x11DA / PID 0x0012**, serial **126-5248** | memory |
| Linux access | `libusb`/`pyftdi` claims it freely (kernel `ftdi_sio` ignores 0x11DA); `uaccess` udev rule grants non-root access **after a physical replug** | `udev/99-tekscan.rules` |
| Exact init sequence | CBUS3 reset pulse (`set_bitmode 0x80`→`0x88`, CBUS) → **750000** baud → **8N1** → flow none → latency → end in `set_bitmode 0x00` (RESET/UART) so libusb can read | `tekscan_connector/protocol.py` |
| Wire frame format | poll one register byte → reply **`[value][~value]`** (value + bitwise-complement checksum); `value` = **8-bit force count 0–255** | `protocol.py::read_register` |
| Calibration | 2-point raw→force (`STANDARD_GRAVITY=9.80665`), verified | `tekscan_connector/calibration.py` |
| The binary | `ElfMPort.exe` (3.8 MB PE32) extracted from the installer | `vendor/elf_extracted/App_Executables/ElfMPort.exe` |

**Decoded landmark functions in `ElfMPort.exe`** (from prior Ghidra passes, `re/logs/decomp*.log`):

| Address | Role |
|---|---|
| `FUN_00446f30` | `CCommHandler` connect — the full FT_* init sequence above |
| `FUN_00409b60` | `OnConnect` — calls `FUN_0040c0f0(*(short*)(param_1+0x82))` = **select channel** |
| `FUN_0040c0f0` | **select-channel** builder — ⭐ THE PRIME TARGET (see §4) |
| `FUN_0040cbd0` | `sendCommand` — transport, retries 15× / 333 ms |
| `FUN_00432ad0` | `sendAndAck` — posts command to the async message queue |
| `FUN_00409d50` | `ButtCellDevice::OnNewDataAvailable` — parses reply `[0][value][~value]`, check `byte2 == (~byte1 ^ byte0)` |
| Comm vtable `@0x5d2134` | `WritePort = FUN_004471a0`, `ReadPort = FUN_004468b0` |

## 3. The SINGLE remaining gap

The latest Ghidra decode is explicit: **there are no secret commands and no streaming.** The device is poll-driven: you write a register/channel byte, it replies `[value][~value]`. Two empirical facts pin the gap:

- **255 is the no-load idle rail** (the manual's no-load maximum). So a live sensor channel reads **255 with nothing on it** and should **drop** under force.
- Candidate sensor registers from live sweeps: **`0x61`, `0x70`** (both read `ff 00` = 255 = idle rail → exactly what an unloaded live channel looks like), and **`0x44`** (read `02 fd` = 2).

So the gap is precisely: **which byte does `ButtCellDevice` poll to read the live ButtCell force?** Equivalently — **what literal byte does the select-channel path (`FUN_0040c0f0`, fed the channel index from `+0x82`) ultimately write to `WritePort`?**

Once that byte is known, reading force on Linux is: `init → write(byte) → read 2 → value = data[0] → force = a*value + b`.

## 4. OVERNIGHT METHOD (device-free, fully autonomous)

**Target:** extract, *statically from the binary*, the exact register/channel byte the live ButtCell read uses — so the morning test is **one deterministic command**, not a 256-register guessing sweep.

This needs **only the binary + Ghidra**. No device. No replug. No Vivek. Fully reproducible. Grind all night.

### 4a. The fast Ghidra project (now built)
A **saved, pre-analyzed** Ghidra project lives at `re/project/ElfMPort.{gpr,rep}`. All decompile passes use `-process` (seconds), never `-import` (minutes). Invocation template:

```bash
P="/home/vivekkarmarkar/Python Files/tekscan-connector"
JAVA_HOME="$P/re/jdk21" "$P/re/ghidra/support/analyzeHeadless" \
  "$P/re/project" ElfMPort \
  -process ElfMPort.exe -noanalysis \
  -scriptPath "$P/re/scripts" -postScript <YourScript>.java \
  > "$P/re/logs/<run>.log" 2>&1
```

### 4b. The trace to run
1. Decompile **`FUN_0040c0f0`** (select-channel). Follow its argument (channel index from `+0x82`) through any lookup table / arithmetic into the literal byte(s) it hands to `sendCommand`/`WritePort`. **That byte is the answer.**
2. Decompile **`FUN_0040cbd0`** (`sendCommand`) and **`WritePort = FUN_004471a0`** to confirm how the byte reaches `FT_Write` — and whether a channel index is offset/encoded (e.g. `0x60 + ch`, which would explain `0x61` = channel 1).
3. Cross-check against **`FUN_00409d50`** (`OnNewDataAvailable`): the producer writes byte X, the consumer reads back `[value][~value]` for the same X. Confirm X is consistent on both sides.
4. Look for a **channel/register table** in `.rdata` (an array of poll bytes indexed by channel). FT245/ButtCell devices commonly map channel→byte via a small table; dumping it gives every channel's poll byte at once.
5. If `FUN_0040c0f0` dissolves into virtual dispatch, walk the comm vtable `@0x5d2134` and the message-queue consumer (`FUN_00432ad0` → worker thread) to find where the queued command's opcode byte is materialized before `WritePort`.

### 4c. Orchestration
Run this as a **multi-agent Ghidra workflow** (ultracode is on): fan out one agent per landmark/branch (select-channel chain, sendCommand/WritePort, OnNewDataAvailable cross-check, `.rdata` table scan, vtable/queue walk). Each returns structured findings: `{function, opcode_candidates:[{byte, evidence, confidence}], notes}`. Then **adversarially verify** the top candidate: does it reconcile producer↔consumer, and does it explain the live observations (`0x61`/`0x70`→255 idle, `0x44`→2)? Synthesize a single ranked answer.

## 5. SUCCESS CRITERIA (what "done" means tonight)

Tonight is a success if `re/FINDINGS.md` contains, with binary evidence:

1. **The live-read byte** (or a short ranked list if ambiguous), e.g. "poll `0x61` = ButtCell channel 1; channel→byte map is `0x60 + ch`."
2. **The full deterministic sequence**: `init → write([byte]) → read 2 → value=data[0]`, with the checksum rule restated.
3. A **ready-to-run probe** `probe/scan_attempt.py` that: opens at the correct init, polls the derived byte(s) continuously for ~20 s, prints value + force, and **logs every frame via `triallog.log_trial(...)`** to `probe/results/`. (Uses the new logging helper so the morning trial is captured, not narrated.)

If the byte cannot be pinned with certainty, success is a **ranked candidate list** (each with its binary evidence) + a `scan_attempt.py` that sweeps exactly those candidates — so the morning test is still short.

## 6. MORNING CAPSTONE (needs Vivek — the only human-in-the-loop step)

1. **Physically replug** the handle (power-cycle; this also applies the udev ACL).
2. Run `probe/scan_attempt.py`.
3. With the sensor inserted, **press the pad / set the 500 g (then 1000 g) weight** on it.
4. **Confirm the value drops from 255** under load and recovers when released. That single observation closes the loop: the byte is confirmed, calibration's 2 points (0 g = 255-ish, 1000 g = loaded value) are captured, and `force = a*value + b` goes live.

Everything up to step 4 is done overnight without him.

## 7. RUNNING SCOREBOARD (append-only; newest at bottom)

- 2026-06-04 01:35 — Persisted toolchain out of `/tmp` into `re/` (Ghidra 12.1 + JDK21 + scripts + 6 decomp logs + trial baselines). Built `probe/triallog.py` (results logging, self-test passed). Building saved Ghidra project `re/project/ElfMPort`. Wrote this problem statement.

## 8. GUARDRAILS

- **Never touch working code.** `protocol.py`, `calibration.py`, the existing `probe/*.py`, the udev rule — all frozen. Only ADD new artifacts (`re/`, `probe/scan_attempt.py`, `probe/triallog.py`, `re/FINDINGS.md`).
- **No device needed overnight.** Static RE only. The device wedges and needs a replug only Vivek can do — so do not depend on it before morning.
- **Log everything.** Ghidra → `re/logs/`. Findings → `re/FINDINGS.md`. Live trials (morning) → `probe/results/` via `triallog`.
- **Honest scoreboard.** If a pass is inconclusive, write that. Rank candidates by evidence; never present a guess as confirmed.
- **Update memory** with any new durable fact (esp. the live-read byte once found).

# problem_statement.md — Crack the Tekscan ELF live-read on Linux (self-sufficient overnight)

**Author:** Claude (self-authored). **Written:** 2026-06-04, ~02:10 local. Vivek asleep; laptop on, plugged in, no reboot.
**Supersedes the model in `OVERNIGHT_GOAL.md`** (which assumed poll-a-register). The model is now corrected: **the device is a free-running STREAMING device armed by a Set-Frame-Rate command.** This file is the authoritative overnight plan.

---

## 1. The corrected, doc-confirmed model (what is now KNOWN)

The Tekscan ELF handle (FTDI FT232R, USB `11DA:0012`) is **NOT poll/response**. It is **free-running streaming**:

1. Host opens + inits the handle (DONE — `tekscan_connector/protocol.py`: CBUS3 reset, 750000 8N1, end in UART mode).
2. Host sends a **SetFrameRate command** with a non-zero frame period. ← **THE MISSING STEP.**
3. Device then **streams `[value][~value]` frames continuously** at the set rate, no per-frame request from the host.
4. `value` = 8-bit force count. **DIRECTION (corrected): no-load ≈ LOW (~0); force RAISES it toward 255** (typ. loaded ≈190/255). Checksum: `value ^ next == 0xFF`.

**Evidence this is right (triangulated):**
- **Binary (ElfMPort.exe):** the "Set Frame Rate" UI action → `FUN_00457a30` (fan-out) → `FUN_0040bd00` (SetFrameRate writer) → virtual encode `(*(*obj+0x14))(&cmd, rate)` → `FUN_0040cbd0` sendCommand → `FUN_00432ad0` sendAndAck → `FUN_004471a0` WritePort. The `CommunicationThread` (`FUN_004313a0`/`FUN_004319d0`) is **event-driven** (`WaitForMultipleObjects`, 40 ms) and issues **NO per-frame write** → device free-runs. Reply parser `FUN_00409d50` has a **case `0x39`** (rate-ACK): `rate = 375000 / framePeriod`.
- **Official manual (Rev P) + patent US7591165B2:** 8-bit 0–255; default 8 Hz, 10–200 Hz standard, ~960 Hz hw / 5.7 kHz hi-speed; **force RAISES the count** (no-load low, typ ~190/255); calibration = point/2-point + sensitivity.
- **Public SDK (SobinovLab/akipina, wraps closed TekAPI.dll):** acquisition armed by `TekInitializeSensor(serial, framePeriod_µs)` (`10000 µs → 100 Hz`, i.e. `Hz = 1e6/period_µs`). Confirms **rate-by-period arms acquisition**.

**Two corrections the research forced (DO NOT regress):**
- **Force direction:** earlier notes said "255 = no-load, drops under force." WRONG. The `255` we kept reading was the **`0xFF` NOT-READY sentinel** (device wasn't streaming). Correct: no-load ≈ **low**, force **raises**. Morning test must look for the value to **RISE** under load (but treat it direction-agnostically: any reproducible change tied to force confirms the channel).
- **Rate formula layers:** wire `Hz = 375000/framePeriod_wire` (binary; `375000 = 750000/2 = baud/2`) vs SDK `Hz = 1e6/period_µs`. Both true at their layer (factor 0.375). Use the **wire** formula for the bytes we send.

**Honest caveat:** the `[value][~value]` framing, the `0x39` ACK, and the SetFrameRate request bytes are **binary-only** findings — no public capture of `11DA:0012` exists. That's expected (proprietary); the binary is authoritative for bytes. Treat them as high-confidence-but-unverified-on-wire until the morning capstone.

## 2. The single remaining gap → the exact LEAF

**Recover the SetFrameRate request packet bytes.** Formally (see Formal Decomposition #2, in chat + below):

> **LEAF = `*(command_encoder_vtable + 0x14)`** — the SetFrameRate command-encoder, reached from the virtual call site inside `FUN_0040bd00`. Resolving this one node yields `opcode_SFR` + the 16-bit `framePeriod` packing (+ any checksum). The select-channel encoder at slot **`0xc`** (the old target) is now just a cross-check that I've found the right vtable.

## 3. Overnight method (device-free, fully autonomous)

Toolchain is persistent + fast (saved project, `-process` ≈ 10 s). Invocation:
```bash
P="/home/vivekkarmarkar/Python Files/tekscan-connector"
JAVA_HOME="$P/re/jdk21" "$P/re/ghidra/support/analyzeHeadless" "$P/re/project" ElfMPort \
  -process ElfMPort.exe -noanalysis -scriptPath "$P/re/scripts" -postScript <Script>.java \
  > "$P/re/logs/<run>.log" 2>&1
```
**Resolution procedure (the algorithm from Formal Decompose #2):**
1. Decompile `FUN_0040bd00` with disassembly/P-code; locate the exact `(*(*obj+0x14))(...)` call site; identify `obj` and where its vptr is stored.
2. Resolve `obj`'s **encoder vtable address V** (trace constructor / vptr store; or its caller `FUN_00457a30`).
3. `leaf := *(V + 0x14)`; also note `*(V + 0xc)` (select-channel, INV4 cross-check).
   - **FALLBACK** if heap type is ambiguous: enumerate every `.rdata` vtable whose slots point into the `0x40bxxx`/`0x40cxxx` builder cluster; pick the table whose slot `0xc` == select-channel encoder (`FUN_0040c0f0`'s callee). That uniquely IDs the table.
4. Decompile `leaf`: extract literal `opcode_SFR`, the 16-bit period packing (endianness/offset), any checksum byte.
5. Cross-validate: INV3 (opcode pairs with `0x39` ACK), INV4 (slot `0xc` = select-channel). Optional INV5: confirm the same bytes at `WritePort` `FUN_004471a0`.
6. Emit byte template `SFR(Hz) = [opcode_SFR | pack16(375000/Hz) | checksum?]`. Precompute candidates: **8 Hz → framePeriod 46875 (0xB71B)**, 100 Hz → 3750 (0x0EA6), 200 Hz → 1875 (0x0753).

**Orchestration (ultracode):** run as a Ghidra-backed multi-agent workflow. Because the project lock is single-writer, **serialize Ghidra passes** (one decompile dump up front), then **fan out analysis agents** over the text + adversarially verify the candidate opcode against INV2–INV5. Loop until the leaf is resolved or all encoder-vtable candidates are exhausted and ranked.

## 4. Success criteria (what "cracked" means tonight)

`re/FINDINGS.md` contains, with binary evidence (decompiled snippets + addresses):
1. **`opcode_SFR`** (concrete literal) and the **full SetFrameRate packet layout** (opcode + period16 + checksum), satisfying the success predicate `(opcode literal) ∧ INV2 ∧ INV3 ∧ (INV4 ∨ INV5)`.
2. The complete **start-streaming → read sequence**: `init → write(SFR(Hz)) → loop{ read 2 bytes; assert v^~v==0xFF; value=byte0 } → force=calib(value)`.
3. A ready-to-run **`probe/scan_attempt.py`** that: opens at the correct init, writes `SFR(Hz)` for Hz∈{8,100}, reads the stream for ~20 s, prints/parses frames, and **logs every frame via `triallog.log_trial(...)`** to `probe/results/`.

If the opcode can't be pinned with certainty, success = a **ranked candidate list** (each opcode with its vtable/evidence) + a `scan_attempt.py` that tries each, so the morning test is still short.

## 5. Morning capstone (the only human step — Vivek)

1. **Physically replug** the handle (power-cycle → also applies the udev ACL; clears any wedge).
2. Run `probe/scan_attempt.py`.
3. Sensor inserted: **press the pad / add the 500 g then 1000 g weight.**
4. **Confirm the streamed value CHANGES with force** (expected: rises from a low no-load baseline). That closes it: opcode confirmed, 2 calibration points captured (no-load + 1000 g), `force = a·value + b` goes live.

## 6. Guardrails (frozen)

- **Never touch working code:** `protocol.py`, `calibration.py`, existing `probe/*.py`, the udev rule. ADD only: `re/*`, `probe/scan_attempt.py`, `re/FINDINGS.md`, new `re/scripts/*.java`.
- **No device needed overnight.** Static RE only. The device wedges and needs a replug only Vivek can do.
- **Log everything:** Ghidra → `re/logs/`; findings → `re/FINDINGS.md`; (morning) live trials → `probe/results/` via `triallog`.
- **Honesty:** rank by evidence; never present a guess as confirmed; if a vtable resolution is ambiguous, say so and enumerate candidates.
- **Update memory** with the resolved opcode once found.

## 7. State pointers (resume cold from here)

- Model + plan: **this file** (authoritative) and `OVERNIGHT_GOAL.md` (older, poll-model — superseded; keep for history).
- Decompiled call-graph: `re/logs/chain_dump.clean.c` (152 fns, 2-deep) + `re/logs/acq_handlers.c`, `comm_thread.clean.c`, `setrate_callers.clean.c` (from the human-emulate RE agent).
- Key addresses: writer `FUN_0040bd00`; UI fan-out `FUN_00457a30`; transport `FUN_0040cbd0`→`FUN_00432ad0`→WritePort `FUN_004471a0`; consumer `FUN_00409d50` (case `0x39`, `rate=375000/period`); select-channel `FUN_0040c0f0` (encoder slot `0xc`).
- Memory: `…/memory/tekscan-elf-research-facts.md` (+ this run's additions).

## 8. Scoreboard (append-only)

- 02:10 — Model corrected to STREAMING-after-SetFrameRate (human-emulate 3-agent convergence + doc confirmation). Force direction corrected (no-load low, rises with force; old 255 = NOT-READY sentinel). Leaf pinned: `*(encoder_vtable+0x14)` from `FUN_0040bd00`. Next: resolve the encoder vtable → opcode_SFR.
- 02:55 — Opcode `0x39`='9'=SetFrameRate confirmed (dispatcher `case 0x39` + automation `FUN_0045ca80(0x39,"SetFrameRate",1)`). Built first scan_attempt.py + FINDINGS.md. Launched adversarial verification workflow.
- 03:30 — **REQUEST PAYLOAD DECODED** (adversarial workflow caught that I'd half-read the encoder). `FUN_0045e730` builds payload = **`[band][~value_hi][~value_lo]`** (one's-complement BE). `value=int((1/Hz−16e‑6)·clock_band+0.5)`, band/clock per Hz range; constants live-read. Payload: 8Hz=`30 48 ea`, 100Hz=`50 15 ff` (round-trips perfectly).
- 03:55 — **Full automation API mapped** (`FUN_0045ca80` callers): dispid≡wire opcode. `0x30 CollectSingle`(1-frame poll) … `0x39 SetFrameRate` … `0x3d StartRecording` … `0x49 ReadFlashPage`. **No SelectChannel method** → single-sensor likely needs no channel-select (red-team's top risk defused). Empty-payload commands (StartRecording) prove the **opcode is prepended** → SetFrameRate wire = **`[0x39]+payload`** (8Hz=`39 30 48 ea`, 100Hz=`39 50 15 ff`). Final `scan_attempt.py`: prefixed form rank-1, bare rank-2, hedges, + **CollectSingle(`0x30`) poll fallback** to read force even without streaming. FINDINGS.md + memory updated. Remaining = pure empirical (transport wrapping) → the morning probe resolves it.

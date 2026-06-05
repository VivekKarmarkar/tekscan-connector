# re/FINDINGS.md — Tekscan ELF protocol: overnight RE results (2026-06-04)

Authoritative record of what the overnight reverse-engineering established, with
binary evidence. Pairs with `../problem_statement.md` (plan) and the memory file.

## TL;DR

The handle is a **free-running streaming device**, started by a **SetFrameRate
command**. The exact wire command is now **DECODED** from the request encoder
`FUN_0045e730` (not guessed):

```
wire  = [band] [~value_hi] [~value_lo]              # one's-complement, big-endian
value = int( (1/Hz - 16e-6) * clock_band + 0.5 )    # per-band timer reload
   6-11Hz band 0x30 clk 375000     46-91Hz  band 0x00 clk 3000000
  12-22Hz band 0x20 clk 750000     92-183Hz band 0x50 clk 6000000
  23-45Hz band 0x10 clk 1500000    >=184Hz  band 0x40 clk 12000000   (<6Hz: no cmd)
```
Payload examples: **8 Hz → `30 48 ea`**, **100 Hz → `50 15 ff`**, **200 Hz → `40 16 5f`**.

**Likely full wire frame = `[0x39] + payload`** (the dispid is prepended by the
transport — proven because `StartRecording`/`CollectSingle` build *empty* payloads
yet must put their opcode on the wire). So **8 Hz → `39 30 48 ea`**, **100 Hz →
`39 50 15 ff`**. The scanner tries the prefixed form first, bare second.

**Full command set (automation dispid = wire opcode, from `FUN_0045ca80` callers):**
`0x30` CollectSingle (1 frame, bare `0x30`) · `0x32/0x33` Get/SetReferenceVoltage ·
`0x39` SetFrameRate · `0x3d` StartRecording (bare) · `0x3e` StopRecording ·
`0x40` GetSN · `0x41` SetSN · `0x42/0x43` Get/SetWiFiSettings · `0x44` GetFWversion ·
`0x45` Reboot · `0x46` FlashErasePage · `0x47` WriteWord · `0x48` WriteRow · `0x49` ReadFlashPage.
**No `Connect`/`SelectChannel` automation method exists** → a single-sensor handle
likely needs no channel-select. `CollectSingle` (`0x30`) is a single-frame poll —
the scanner's fallback to read force even if continuous streaming doesn't engage.

Once sent, the device pushes **`[value][~value]`** frames continuously; `value` is
the 8-bit force count (**no-load LOW, RISES with force**). `0x39`='9' is the
SetFrameRate *dispatch id / reply opcode*; it is **not** a literal wire byte of the
request. Two empirical unknowns remain for the morning probe: whether the transport
wraps the 3 bytes, and whether a channel-select must precede SetFrameRate.

> **CORRECTION (2026-06-04, adversarial verification):** an earlier draft of this
> file said "the byte layout is not statically recoverable." That was WRONG — the
> encoder `FUN_0045e730` fully reveals it (band + one's-complement, above). The
> error was reading only the function's first 40 lines (the automation
> registration) and stopping before the encoder body. Constants verified live:
> C1=1.0, C2=16e-6, C3=0.5, clocks {375k…12M} at `0x5cc470/0x5d38c0/0x5ccc08/0x5d38c8..f0`.

## What was PROVEN (binary evidence)

| Finding | Evidence (addr / source) |
|---|---|
| **Streaming, not poll/response** | `CommunicationThread` `FUN_004313a0`/`FUN_004319d0` is event-driven (`WaitForMultipleObjects`, 40 ms) and issues **no per-frame write**. Device free-runs after rate is set. |
| **Acquisition trigger = SetFrameRate** | UI "Set Frame Rate" → `FUN_00457a30` (fan-out over connected devices) → `FUN_0040bd00` (writer) → encode via virtual slot `0x14` → `FUN_0040cbd0` sendCommand → `FUN_00432ad0` sendAndAck → `FUN_004471a0` WritePort. |
| **Opcode `0x39`='9' = SetFrameRate** | (1) Response dispatcher `FUN_00409d50` **`case 0x39`** = rate ACK. (2) OLE automation registration **`FUN_0045ca80(0x39,"SetFrameRate",1)`** binds dispid `0x39` to the method named "SetFrameRate". Automation dispid ≡ wire opcode. |
| **Rate formula `Hz = 375000/period`** | `case 0x39`: `*(short*)(dev+0x154) = 0x5b8d8 / period`, `0x5b8d8 = 375000 = 750000 baud / 2`. |
| **Period is 16-bit, big-endian (reply side)** | `case 0x39`: `period = byte[2]*0x100 + byte[3]` read from the reply payload at `*(msg+0x20)` offset 2–3. |
| **Frame format `[value][~value]`** | `ButtCellDevice::OnNewDataAvailable` `FUN_00409d50`; checksum `value ^ next == 0xFF`. Confirmed earlier vs live bytes (`ff 00`, `02 fd`). |
| **8-bit value, rises with force** | Official ELF Manual Rev P + patent US7591165B2: no-load = high R = LOW count; force lowers R → RAISES count (typ. loaded ≈190/255). |
| **Protocol opcode set (ASCII)** | Dispatcher cases: `0x30 0x32 0x33 0x39 0x3e 0x40 0x42 0x43 0x44 0x46 0x47 0x48` = `'0' '2' '3' '9' '>' '@' 'B' 'C' 'D' 'F' 'G' 'H'`. |

## Remaining unknowns (now only TWO, both empirical)

The request *format* is decoded (above). What the static logs do **not** settle:

1. **Transport wrapping.** `FUN_0045e730` builds the 3-byte vector `[band][~hi][~lo]`
   and returns it; whether `WritePort`/`FT_Write` (`FUN_004471a0`) sends exactly
   those 3 bytes or adds a prefix/checksum/length/terminator is unconfirmed. The
   scanner hedges with `decoded+0x39pre`, `decoded+xorck`, `decoded+CR`, raw
   (non-complement), and a no-band form.
2. **Channel-select prerequisite.** `ButtCellDevice::OnConnect` (`FUN_00409b60`)
   issues select-channel (`FUN_0040c0f0`, channel from `dev+0x82`) at connect. On a
   single-sensor handle a default channel may suffice; if SetFrameRate-alone yields
   no stream, the next step is to decode select-channel's encoder (sibling of
   `FUN_0045e730`) and prepend it.

The device resolves both in one short run: it streams only for the correct
sequence/framing.

## Candidate packets (ranked) → `probe/scan_attempt.py`

Primary = the decoded command; the rest hedge transport wrapping. 8 Hz example
(`band=0x30`, value=46869=0xB715, `~value`=0x48EA) / 100 Hz (`band=0x50`, value=59904, `~`=0x15FF):

| Rank | Label | 8 Hz | 100 Hz |
|---|---|---|---|
| 1 | decoded `[band,~hi,~lo]` | `30 48 EA` | `50 15 FF` |
| 2 | decoded + 0x39 prefix | `39 30 48 EA` | `39 50 15 FF` |
| 3 | decoded + xor-checksum | `30 48 EA 92` | `50 15 FF BA` |
| 4 | decoded + CR | `30 48 EA 0D` | `50 15 FF 0D` |
| 5 | band + raw BE (no complement) | `30 B7 15` | `50 EA 00` |
| 6 | 0x39 + ~BE (no band) | `39 48 EA` | `39 15 FF` |

Detection: after sending a candidate, read ~2.5 s **sending nothing**; ≥6 valid
`[value][~value]` frames ⇒ streaming started = winner (a single poll reply = 1
frame). 100 Hz is tried first (~250 frames in 2.5 s = large margin).

## Morning capstone (needs Vivek + device)

1. **Physically replug** the handle (power-cycle / clears wedge / applies udev ACL).
2. `cd "<project>" && .venv/bin/python probe/scan_attempt.py`
3. When it reports a WINNER and starts the 5 s capture, **press the pad / add the
   500 g then 1000 g weight**. Confirm the streamed value **changes** (expected:
   rises from a low no-load baseline).
4. Record the winning packet here, set the live-read sequence, capture the 2
   calibration points (no-load + 1000 g), and `force = a·value + b` goes live.

## Read sequence (once the winning packet is known)

```
init (tekscan_connector/protocol.py)            # CBUS3 reset, 750000 8N1, UART
write( SetFrameRate packet )                    # e.g. 39 B7 1B  → device streams at 8 Hz
loop:
    read 2 bytes  ->  v, c
    assert (v ^ c) == 0xFF                       # frame checksum
    value = v                                    # 8-bit force count
    force = a*value + b                          # 2-point calibration
```

## Ghidra logs (all under re/logs/, reproducible via re/scripts/)

- `chain_dump.clean.c` — 152-fn 2-deep decompile of the read path.
- `acq_handlers.c` — frame-rate writer `FUN_0040bd00`, full response dispatcher
  `FUN_00409d50` (all opcode cases incl. `case 0x39`).
- `comm_thread.clean.c` — `CommunicationThread` (event-driven, no per-frame write).
- `setrate_callers.clean.c` — UI fan-out `FUN_00457a30`.
- `find_opcode.clean.txt` — opcode `0x39` materialization sites (incl. the
  `FUN_0045ca80(0x39,"SetFrameRate",1)` automation registration).
- `global_encoder*.clean.txt`, `factory_scan.clean.txt`, `dump_ctor.clean.txt` —
  the (inconclusive) factory-vtable resolution attempts; kept for the record.
- Scripts: `DecompChannelChain`, `DumpCtor`, `ResolveEncoder`, `GlobalEncoderScan`,
  `GlobalEncoderScan2`, `FindOpcode`, `VtableFactoryScan` (`.java` in re/scripts/).

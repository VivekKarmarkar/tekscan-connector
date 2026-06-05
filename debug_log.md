# Debug Log — The Wedged Handle Saga (2026-06-05 → 2026-06-06)

How the Tekscan FlexiForce ELF handle went from *streaming live force*, to *stone dead and immune to every reset we knew*, and back to *working on demand* — and the single dumb variable that explained all of it.

---

## TL;DR — the fix

**The handle arms exactly ONCE per *real* power-up.** Once that single arming "shot" is spent, it sits on the `0x00`/`0xFF` not-ready rail at ~0.2 B/s and *nothing* short of a real power-up brings it back.

The variable nobody isolated for a full day: **power-down DURATION.**
- A 2 s replug, or even a deliberate 15–20 s power-cycle, is **not** long enough to count as a power-up to the MCU → the next arm is still wedged.
- A **long** power-down (≥ ~60 s, minutes safer, overnight bulletproof) **does** count → the next arm streams.

**The working recipe:**
1. Unplug the handle, wait **≥ ~60 s** (overnight is bulletproof), strip seated, replug.
2. Launch `probe/gui_web.py` **ONCE** — its single open+arm consumes the fresh shot.
3. **Hold that session — never re-arm.** At ~11 fps data flows steadily enough that the `STALL=2.0` watchdog never reconnects, so it stays live. Every re-arm *without* a new long power-down burns the shot → back to wedged.

Confirmed reproducible 2026-06-06: hard press hit **peak 196/255** live.

---

## The hardware, briefly

- Tekscan FlexiForce **ELF** handle, model **B201-H** (high range). FTDI **FT232R** bridge, USB **VID 0x11DA / PID 0x0012**.
- Linux-native, no vendor SDK, no Windows. Driven through `pyftdi` 0.57.2.
- Decoded protocol (see `re/FINDINGS.md`): @ **1,000,000 baud** —
  `SetReferenceVoltage(0x32, 0xFF)` → `SetFrameRate(0x39, 0x30, 0x48, 0xEA)` → `StartRecording(0x3d)` → free-running force bytes.
- `0xFF` is the **"not-ready" sentinel**, not a force value. `gui_web.py`'s reader filters it (added during this saga) so it stops drawing a fake 0↔255 sawtooth when the device is half-armed.

---

## Day 1 — 2026-06-05

### Morning: it works
`probe/gui_web.py` streamed clean live force at **~60 B/s**, readings **19–57** under finger presses. The split-screen demo video was recorded. Everything looked solved.

### Later that day: it dies
After a lot of start/kill cycling, probing, and re-arming, the handle went **persistently wedged**:
- Emits only its idle rail: `0x00` (force) + `0xFF` (not-ready), at **~0.2–0.3 B/s** (healthy is ~60).
- The force value never leaves `0`. Pressing the pad changes nothing.

### Everything tried — ALL failed identically (still `0xFF`, ~0.2 B/s)
- 2 s replug; full **15–20 s power-cycle**; `USBDEVFS_RESET` ioctl (re-enumerates the device).
- A red-team workflow's 5 ranked fixes:
  - robust CBUS3 reset pulse (200 ms low / 200 ms high holds, vs the stock ~20 ms),
  - explicit CBUS mask toggle (`(DIR<<4)|val`),
  - **DTR/RTS** reset (the method `probe/wake_attempt.py` uses),
  - FT232R **EEPROM CBUS** read (errored: `ee.properties` is a set, not a dict — never actually read),
  - a persist-the-winning-pulse step.
- The original `probe/handshake.py` / `probe/wake_attempt.py` wake sequences.
- A **fresh power-cycle + reseated FlexiForce strip + a single clean arm (no GUI/watchdog) + active pressing** → *still dead.*

### The clues we had (and misread)
- `probe/handshake.py` comment, written during the original RE:
  > "one response per physical power-up; the CBUS reset is **NOT** a true power cycle."
  This was the answer the whole time. We read it as "the one-shot timing," not "you need a real, long power-down."
- pyftdi's `open_from_device()` already does `purge → SIO reset → set_bitmode(0, RESET) → set_latency_timer` on **every** open, and `ftdi_sio` wasn't even loaded — so "stuck in bitbang / kernel grabbed the port / stale cache" were all ruled out. Whatever was wrong survived a fresh process, a USB reset, *and* a 20 s power-cycle.
- The red-team converged hard: the blocker is **device STATE, not solution cardinality**; the cure is **observability** (capture a working vs. wedged arm and diff), not more reset-pulses. Correct in spirit — we just hadn't found the state variable.

### The detour worth keeping: "is the solution unique?"
A long thread on whether the reverse-engineered solution was *unique* (→ traceable bug) or *non-unique* (→ lucky, footprints dried). Formalized as a state-machine reachability question. Verdict: the **command sequence** is unique (Reading A, true-but-near-tautological); **model identifiability** is a different axis (Reading B, where path-count says nothing). And critically — neither explains the wedge: the device was simply in state `S′ ≠ S0` (arming latch spent), so the valid `S0→SN` path didn't apply. The bug was a **start-state mismatch you can't observe**, not an ambiguous path. (A blind red-team on the framing also, fairly, flagged the prior over-eager agreement as sycophancy. Noted.)

---

## Day 2 — 2026-06-06 — the breakthrough

The one new variable: the handle had sat **unpowered overnight** — far longer than any deliberate power-cycle we'd tried.

### The two arms that cracked it
- **1st arm** (fresh from the overnight plug-in): **~11 B/s**, real-ish acks (`vref ff00`, `rate 0fff00`), force moved off zero (reached 2). → *working.*
- **2nd arm** (immediately after, no replug): **0.2 B/s**, `vref (none)`, `rate 00ff00ff`, dead. → *wedged.*

That side-by-side is the whole proof: **one good arm per power-up.** The overnight rest didn't "heal" anything — it handed us a *fresh shot*, and the first arm caught it. The second arm spent it.

This also retroactively explains Day 1: the 15–20 s power-cycle wasn't long enough to register as a power-up, so even its "first" arm was already on a spent/stale shot. Every clever reset failed for the *same* reason — none was a long-enough power-down.

### Landing a live session
- Asked for a **~60 s** power-down + replug.
- Launched `gui_web.py` **once** → `status=streaming` steady, ~11 fps, sample count climbing, **no reconnect thrash** (the steady ~11 B/s keeps the `STALL=2.0` watchdog from re-arming, so the single good shot is held).
- A light touch read ~2; a **hard press hit `peak 196/255`** — full range, *higher* than Day 1's 19–57. Fully working.

### Residual (cosmetic)
- Frame rate is **~11 fps** now vs **~60 fps** on Day-1 morning — chart updates chunkier; the readings themselves are full-range and fine. Possibly the `SetFrameRate`/`SetReferenceVoltage` config only partially takes on this class of power-up; not chased, because it works.

---

## Open questions (optional curiosity — not needed to make it run)

1. **Why does a short power-cycle not count as a power-up?** Likely USB bus-power capacitor hold-up keeping the MCU rail alive across a brief unplug, or a brown-out threshold the MCU never crosses in <~minute. A `usbmon` capture of a working vs. wedged arm + an O-scope on the rail would settle it.
2. **What exactly fills/spends the arming latch?** Is the CBUS3 reset even reaching the pin (the EEPROM CBUS mux was never successfully read — fix the `ee.properties` iteration), or did the morning arm come from the physical power-up alone?
3. **The ~11 vs ~60 fps gap.** Whether the rate/vref commands fully apply seems power-up-dependent.

None of these block usage. They're "understand *why*," not "make it work."

---

## Lessons

- **We measured the power-down in seconds; the device counts it in minutes.** Every sophisticated fix (CBUS pulses, DTR/RTS, USB resets, EEPROM spelunking, a 5-agent red-team) failed for one unglamorous reason: insufficient power-down. The fix wasn't sharper code — it was *waiting longer.*
- **The honest clue was in our own old comment** (`handshake.py`: "not a true power cycle"). We had the answer on Day 1 and spent a day not believing it.
- **Reproducibility was the real deliverable.** The proof-of-concept's point isn't that you can crack a vendor-locked sensor once — it's that you can lose it, stay honest about being stuck, and get it back *on purpose*, with a recipe.
- **If it ever wedges again:** don't fight it. Unplug, walk away for a minute (or leave it overnight), plug back in, launch once, hold.

---

*Arc: "holy shit it's solved" → "holy shit it's dead and nothing works" → "holy shit it's working again" — ~18 hours. Logged for the next time the rail goes flat.*

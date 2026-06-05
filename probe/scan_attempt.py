#!/usr/bin/env python3
"""
scan_attempt.py — start the Tekscan ELF live stream and capture force.

THE COMMAND IS DECODED (not guessed). The SetFrameRate request encoder
FUN_0045e730 in ElfMPort.exe was fully decompiled (see re/FINDINGS.md). The wire
command is 3 bytes:

    wire = [band] [~value_hi] [~value_lo]            # one's-complement, big-endian
    value = int( (1/Hz - 16e-6) * clock_band + 0.5 ) # per-band timer reload
    band/clock by Hz range (timer prescaler):
       6-11Hz -> 0x30 / 375000      46-91Hz  -> 0x00 / 3000000
      12-22Hz -> 0x20 / 750000      92-183Hz -> 0x50 / 6000000
      23-45Hz -> 0x10 / 1500000     >=184Hz  -> 0x40 / 12000000
    (<6 Hz emits no command.)

Examples:  8Hz -> 30 48 ea   100Hz -> 50 15 ff   200Hz -> 40 16 5f

KNOWN (RE + official manual + patent): streaming device, not poll/response;
once SetFrameRate is sent the device pushes [value][~value] frames continuously;
value is the 8-bit force count and RISES with force (no-load LOW; the 0xFF we saw
before was the NOT-READY sentinel, not a force value); Hz = 375000/period on the
reply side.

STILL EMPIRICAL (this script resolves): (1) whether the transport sends exactly
those 3 bytes or wraps them (prefix/checksum/terminator) — a few hedges are tried;
(2) whether a channel-select must precede SetFrameRate on a single-sensor handle.

Strategy: for each candidate, re-init the handle (CBUS3 MCU reset = clean slate),
send the candidate, then READ ~2.5 s SENDING NOTHING. A non-streaming device
returns ~1 frame; a streaming device keeps emitting. Sustained frames = winner.
100 Hz is tried first (huge stream margin), then 8 Hz. Every attempt is logged.

Run on the morning capstone, AFTER a physical replug of the handle.
"""
import sys, time, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from triallog import log_trial  # noqa: E402

# (lo_hz_inclusive, hi_hz_exclusive, band_byte, timer_clock) from FUN_0045e730.
BANDS = [(6, 12, 0x30, 375000), (12, 23, 0x20, 750000), (23, 46, 0x10, 1500000),
         (46, 92, 0x00, 3000000), (92, 184, 0x50, 6000000), (184, 100000, 0x40, 12000000)]
OVERHEAD_S = 16e-6     # _DAT_005d38c0 — fixed 16 us frame overhead
ROUND_ADD = 0.5        # DAT_005ccc08 — round-to-nearest addend


def encode_setframerate(hz):
    """Return (band, value, primary_cmd_bytes) exactly as FUN_0045e730 builds it."""
    if hz < 6:
        raise ValueError("ELF emits no command below 6 Hz")
    for lo, hi, band, clk in BANDS:
        if lo <= hz < hi:
            value = int((1.0 / hz - OVERHEAD_S) * clk + ROUND_ADD)
            comp = (~value) & 0xFFFF
            return band, value, bytes([band, (comp >> 8) & 0xFF, comp & 0xFF])
    raise ValueError(f"no band for {hz} Hz")


def candidates(hz):
    """Ranked SetFrameRate wire packets. RANK 1 = opcode-prefixed: empty-payload
    commands (StartRecording/CollectSingle) prove the dispid 0x39 is prepended by
    the transport, so the full frame is [0x39][band][~hi][~lo]. Bare form + other
    framings follow as hedges."""
    band, value, payload = encode_setframerate(hz)  # payload = [band,~hi,~lo]
    comp = (~value) & 0xFFFF
    chi, clo = (comp >> 8) & 0xFF, comp & 0xFF
    rhi, rlo = (value >> 8) & 0xFF, value & 0xFF
    op = 0x39
    return [
        ("0x39+[band,~hi,~lo]", bytes([op]) + payload),          # likely real wire frame
        ("[band,~hi,~lo]",      payload),                        # bare encoder payload
        ("0x39+pay+xorck",      bytes([op]) + payload + bytes([op ^ band ^ chi ^ clo])),
        ("0x39+pay+CR",         bytes([op]) + payload + bytes([0x0D])),
        ("0x39+band+rawBE",     bytes([op, band, rhi, rlo])),    # if NOT complemented
        ("0x39+~BE(noBand)",    bytes([op, chi, clo])),          # opcode + complement, no band
    ]


def analyze(raw):
    n = len(raw)
    frames, i = [], 0
    while i + 1 < n:
        v, c = raw[i], raw[i + 1]
        if (v ^ c) == 0xFF:
            frames.append(v); i += 2
        else:
            i += 1
    return {
        "bytes": n, "valid_frames": len(frames),
        "value_min": min(frames) if frames else None,
        "value_max": max(frames) if frames else None,
        "first_values": frames[:16],
        # streaming: many more frames than a single poll reply (which is 1 frame).
        "streamed": len(frames) >= 6,
    }


def read_window(ftdi, secs):
    buf, t0 = bytearray(), time.time()
    while time.time() - t0 < secs:
        d = ftdi.read_data_bytes(256, attempt=2)
        if d:
            buf += d
    return bytes(buf)


def try_candidate(label, packet, hz, read_secs=2.5):
    from tekscan_connector.protocol import TekscanHandle
    h = None
    try:
        h = TekscanHandle()                 # CBUS3 reset pulse = clean slate
        f = h.ftdi
        f.purge_buffers(); time.sleep(0.005)
        f.write_data(packet)                # send the SetFrameRate candidate
        raw = read_window(f, read_secs)     # then listen, sending NOTHING
        info = analyze(raw)
        log_trial("scan_attempt",
                  {"candidate": label, "packet_hex": packet.hex(), "target_hz": hz,
                   "result": info, "raw_head_hex": raw[:96].hex()},
                  meta={"phase": "setframerate-scan", "candidate": label, "hz": hz})
        tag = "  *** STREAMING ***" if info["streamed"] else ""
        print(f"  [{label:22}] {packet.hex():10} -> {info['bytes']:5}B "
              f"{info['valid_frames']:4} frames v=[{info['value_min']},{info['value_max']}]{tag}")
        return info, h
    except Exception as e:
        print(f"  [{label:22}] ERROR: {e}")
        log_trial("scan_attempt_error", {"candidate": label, "error": str(e),
                  "packet": packet.hex()}, meta={"phase": "setframerate-scan"})
        if h:
            h.close()
        return None, None


def capture_stream(h, secs=5.0):
    info = analyze(read_window(h.ftdi, secs))
    log_trial("stream_capture", {"secs": secs, "result": info}, meta={"phase": "live-stream"})
    print(f"\n  STREAM {secs}s: {info['bytes']}B, {info['valid_frames']} frames, "
          f"value range [{info['value_min']},{info['value_max']}]")
    print(f"  first values: {info['first_values']}")
    print("  >>> Now PRESS the pad / add the weight and watch the value MOVE. <<<")
    print("      (no-load should be LOW; force should RAISE it toward 255)")
    return info


def collect_single_poll(n=30, hz=8):
    """Fallback: CollectSingle (opcode 0x30) is a single-frame poll. Send 0x30
    repeatedly and read one [value][~value] frame each time. Works even if
    continuous streaming doesn't engage — gives live force by polling."""
    from tekscan_connector.protocol import TekscanHandle
    print(f"\n--- fallback: CollectSingle (0x30) poll x{n} ---")
    h = None
    try:
        h = TekscanHandle()
        f = h.ftdi
        vals = []
        for _ in range(n):
            f.purge_buffers(); time.sleep(0.002)
            f.write_data(bytes([0x30]))      # CollectSingle
            raw = read_window(f, 0.05)
            info = analyze(raw)
            if info["valid_frames"]:
                vals.append(info["first_values"][0])
            time.sleep(max(0, 1.0 / hz - 0.05))
        log_trial("collectsingle_poll", {"n": n, "values": vals,
                  "vmin": min(vals) if vals else None, "vmax": max(vals) if vals else None},
                  meta={"phase": "collectsingle-fallback"})
        if vals:
            print(f"  CollectSingle returned {len(vals)}/{n} frames, "
                  f"values [{min(vals)},{max(vals)}]: {vals[:20]}")
            print("  >>> If these MOVE when you press the pad, force-read works via polling. <<<")
        else:
            print("  CollectSingle returned no valid frames.")
        return vals
    except Exception as e:
        print(f"  CollectSingle ERROR: {e}")
        return []
    finally:
        if h:
            h.close()


def main():
    print("Tekscan SetFrameRate live-stream starter (command DECODED from FUN_0045e730)")
    print("=" * 70)
    winner = None
    # 100 Hz first: ~250 frames in 2.5 s = huge streaming margin; then 8 Hz.
    for hz in (100, 8):
        band, value, primary = encode_setframerate(hz)
        print(f"--- {hz} Hz: band=0x{band:02x} value={value} primary={primary.hex()} ---")
        for label, packet in candidates(hz):
            info, h = try_candidate(label, packet, hz)
            if info and info["streamed"]:
                winner = (hz, label, packet, h)
                break
            if h:
                h.close()
            time.sleep(0.1)
        if winner:
            break

    if winner:
        hz, label, packet, h = winner
        print(f"\n✅ WINNER: '{label}' packet {packet.hex()} @ {hz} Hz started the stream.")
        capture_stream(h, 5.0)
        h.close()
        log_trial("scan_winner", {"hz": hz, "candidate": label, "packet_hex": packet.hex()},
                  meta={"phase": "RESULT", "note": "this packet starts streaming"})
        print(f"\n   Record in re/FINDINGS.md: SetFrameRate({hz}Hz) = {packet.hex()} ({label}).")
    else:
        print("\n⚠ No candidate started a sustained stream — trying the CollectSingle poll fallback.")
        vals = collect_single_poll(n=40, hz=8)
        if vals and (max(vals) - min(vals) > 0 or len(vals) > 5):
            print("\n✅ FALLBACK WORKS: CollectSingle (0x30) returns force frames by polling.")
            print("   Use polling mode for live force (send 0x30, read [v][~v], repeat).")
        else:
            print("\n❌ Neither streaming nor CollectSingle polling produced moving force data.")
            print("   Next: no automation 'SelectChannel' exists, but OnConnect issues an")
            print("   internal select-channel (FUN_0040c0f0); if needed, decode it and prepend.")
            print("   All attempts logged in probe/results/ for analysis.")


if __name__ == "__main__":
    main()

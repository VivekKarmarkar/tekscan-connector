#!/usr/bin/env python3
"""
stream_1mbaud.py — the SetFrameRate/StartRecording streaming sequence, finally
at the CORRECT baud (1,000,000). Prior attempts ran at 750000 = garbage.

Registers are static config slots (don't move under force), so live force must
come from the STREAM. Test, in one fresh session:
  init @1Mbaud -> SetFrameRate(8Hz, no 0xFF) -> listen 3s (stream alone?) ->
  StartRecording(0x3d) -> listen 8s -> parse [value][~value] frames.

If frames stream, press the pad — the value should move.
Run after a FRESH REPLUG (clean device state).
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402

GOOD_BAUD = 1_000_000
SETRATE_8 = bytes([0x39, 0x30, 0x48, 0xea])   # SetFrameRate @8Hz (no 0xFF)
START = bytes([0x3d])


def listen(f, secs, t0, label, bursts):
    end = time.time() + secs
    while time.time() < end:
        d = f.read_data_bytes(512, attempt=2)
        if d:
            t = round(time.time() - t0, 3)
            bursts.append((label, t, bytes(d).hex()))


def frames_of(bursts, label):
    raw = bytes.fromhex("".join(b[2] for b in bursts if b[0] == label))
    vals, i = [], 0
    while i + 1 < len(raw):
        if (raw[i] ^ raw[i + 1]) == 0xFF:
            vals.append(raw[i]); i += 2
        else:
            i += 1
    return vals, len(raw)


def main():
    print("Streaming sequence @ 1,000,000 baud (run after fresh replug)")
    print("=" * 62)
    h = TekscanHandle()
    f = h.ftdi
    f.set_baudrate(GOOD_BAUD)
    time.sleep(0.01)
    bursts = []
    try:
        # sanity: clean single-byte read at 1Mbaud
        f.purge_buffers(); time.sleep(0.002)
        f.write_data(bytes([0x05]))
        time.sleep(0.03)
        s = f.read_data_bytes(8, attempt=2)
        print(f"  sanity read 0x05 -> {bytes(s).hex()} (expect 00ff)")

        f.purge_buffers(); time.sleep(0.003)
        t0 = time.time()
        f.write_data(SETRATE_8)
        print(f"  sent SetFrameRate {SETRATE_8.hex()}; listening 3s...")
        listen(f, 3.0, t0, "afterrate", bursts)
        v_rate, n_rate = frames_of(bursts, "afterrate")
        print(f"    after SetFrameRate: {n_rate} bytes, {len(v_rate)} frames {v_rate[:12]}")

        f.write_data(START)
        print(f"  sent StartRecording {START.hex()}; listening 8s...")
        listen(f, 8.0, t0, "afterstart", bursts)
        v_start, n_start = frames_of(bursts, "afterstart")
        print(f"    after StartRecording: {n_start} bytes, {len(v_start)} frames")

        total_frames = len(v_rate) + len(v_start)
        allv = v_rate + v_start
        print()
        if total_frames >= 10:
            print(f"  ✅ STREAMING! {total_frames} frames, value range "
                  f"[{min(allv)},{max(allv)}], sample={allv[:20]}")
            print("  >>> PRESS THE PAD / ADD WEIGHT NOW and watch values change <<<")
            # capture a press window
            listen(f, 8.0, t0, "press", bursts)
            vp, _ = frames_of(bursts, "press")
            if vp:
                print(f"  during press: range [{min(vp)},{max(vp)}], sample={vp[:24]}")
        elif n_rate + n_start > 6:
            print(f"  bytes flowing ({n_rate + n_start}) but not clean frames — note framing.")
        else:
            print("  no stream. Bytes seen:", [(b[0], b[2]) for b in bursts][:8])
    finally:
        log_trial("stream_1mbaud", {"baud": GOOD_BAUD, "bursts": bursts},
                  meta={"phase": "stream-at-correct-baud"})
        h.close()


if __name__ == "__main__":
    main()

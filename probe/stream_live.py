#!/usr/bin/env python3
"""
stream_live.py — LIVE FORCE. The full decoded sequence, streaming correctly.

DECODED PROTOCOL (2026-06-04):
  baud  = 1,000,000 (NOT 750000 — that was the bug all along)
  start = SetFrameRate(0x39 + band/period)  then  StartRecording(0x3d)
  stream= ONE byte per frame at the set rate (~10 Hz). byte = 8-bit force value.
          no load = 0; value RISES with force.

This runs the sequence and prints the live force value as single bytes arrive.
Press the pad / add the weight during the run and watch it climb from 0.
Run after a FRESH REPLUG.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402

GOOD_BAUD = 1_000_000
SETRATE_8 = bytes([0x39, 0x30, 0x48, 0xea])   # SetFrameRate @8Hz
START = bytes([0x3d])                          # StartRecording
RUN_SECS = 30.0


def main():
    print("LIVE FORCE STREAM @ 1 Mbaud — press the pad and watch it move")
    print("=" * 62)
    h = TekscanHandle()
    f = h.ftdi
    f.set_baudrate(GOOD_BAUD)
    time.sleep(0.01)
    samples = []
    try:
        f.purge_buffers(); time.sleep(0.003)
        f.write_data(SETRATE_8); time.sleep(0.2)
        f.read_data_bytes(16, attempt=2)          # consume the rate ACK
        f.write_data(START)
        print("  streaming started. PRESS THE PAD / ADD WEIGHT NOW.\n")
        t0 = time.time()
        last_print = -1
        peak = 0
        while time.time() - t0 < RUN_SECS:
            d = f.read_data_bytes(256, attempt=2)
            if d:
                for b in d:
                    samples.append((round(time.time() - t0, 3), b))
                    peak = max(peak, b)
                v = d[-1]                          # latest force value
                # print when the value changes meaningfully, or a 1s heartbeat
                now = time.time() - t0
                if abs(v - last_print) >= 2 or now - getattr(main, "_hb", 0) > 1.0:
                    bar = "#" * (v * 40 // 255)
                    print(f"  t={now:5.1f}s  force={v:3}  peak={peak:3}  |{bar}")
                    last_print = v
                    main._hb = now
        vals = [v for _, v in samples]
        print(f"\n  {len(vals)} frames over {RUN_SECS:.0f}s. "
              f"no-load≈{min(vals) if vals else '?'}, peak={max(vals) if vals else '?'}")
        if vals and max(vals) > 5:
            print(f"  ✅✅✅ LIVE FORCE CONFIRMED — value moved 0 -> {max(vals)} under load.")
            print("  The Tekscan ELF is now readable on Linux. Calibration next.")
        else:
            print("  Value stayed ~0. If you pressed the active pad, the channel may need")
            print("  a sensitivity/gain command; if not, press harder / center of pad.")
    finally:
        log_trial("stream_live", {"baud": GOOD_BAUD, "rate_cmd": SETRATE_8.hex(),
                  "samples": samples, "peak": max((v for _, v in samples), default=0)},
                  meta={"phase": "LIVE-FORCE"})
        h.close()


if __name__ == "__main__":
    main()

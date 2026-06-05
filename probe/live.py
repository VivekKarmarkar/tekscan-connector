#!/usr/bin/env python3
"""
live.py — INTERACTIVE live force readout. Run this YOURSELF in a terminal so you
see the prompt and watch the number move as you press.

Decoded protocol @ 1,000,000 baud:
  SetReferenceVoltage(0x32,Vref) -> SetFrameRate(0x39,..) -> StartRecording(0x3d)
  -> one byte per frame = 8-bit force (no-load 0, rises with force).

Usage:  .venv/bin/python probe/live.py        (run right after a fresh replug)
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402

BAUD = 1_000_000
SETVREF = bytes([0x32, 0xFF])
SETRATE = bytes([0x39, 0x30, 0x48, 0xea])
START = bytes([0x3d])
RUN_SECS = 40.0


def main():
    print("\n=== TEKSCAN LIVE FORCE (run this yourself; watch the number) ===\n")
    h = TekscanHandle()
    f = h.ftdi
    f.set_baudrate(BAUD); time.sleep(0.01)
    samples = []
    try:
        f.purge_buffers(); time.sleep(0.003)
        f.write_data(SETVREF); time.sleep(0.1); f.read_data_bytes(16, attempt=2)
        f.write_data(SETRATE); time.sleep(0.15); f.read_data_bytes(16, attempt=2)
        f.write_data(START)
        # countdown so you can get the weight ready
        for n in (3, 2, 1):
            print(f"  streaming… load the sensor in {n}", end="\r", flush=True); time.sleep(1)
        print("  >>> PRESS THE ROUND PAD / SET THE WEIGHT — watch the bar <<<       \n")
        t0 = time.time(); peak = 0
        while time.time() - t0 < RUN_SECS:
            d = f.read_data_bytes(256, attempt=2)
            if d:
                for b in d:
                    samples.append((round(time.time() - t0, 3), b))
                v = d[-1]; peak = max(peak, max(d))
                bar = "█" * (v * 50 // 255)
                print(f"  force {v:3} / 255  peak {peak:3}  |{bar:<50}|", end="\r", flush=True)
        vals = [v for _, v in samples]
        print("\n")
        print(f"  {len(vals)} frames over {RUN_SECS:.0f}s.  no-load≈{min(vals) if vals else '?'}  "
              f"PEAK={max(vals) if vals else '?'}")
        if vals and max(vals) > 5:
            print("  ✅✅✅ LIVE FORCE CONFIRMED — the Tekscan ELF reads on Linux! 🎉")
        else:
            print("  Still flat. Check: film fully seated in the handle? pressing the round")
            print("  dot at the tip? Try the 1000 g weight squarely on the dot.")
    finally:
        log_trial("live", {"baud": BAUD, "samples": samples,
                  "peak": max((v for _, v in samples), default=0)}, meta={"phase": "INTERACTIVE-LIVE"})
        h.close()
        print()


if __name__ == "__main__":
    main()

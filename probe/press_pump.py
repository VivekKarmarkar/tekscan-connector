#!/usr/bin/env python3
"""
press_pump.py — no live feedback needed. Capture 20 s while you PUMP the sensor.

This environment captures output only AFTER the script ends, so "watch and press"
doesn't work. Instead: you repeatedly press-and-release the sensor for 20 s, and
afterward we read the captured trace — if force registers, the values pulse up and
down, unmistakable even without live feedback.

Decoded protocol @ 1,000,000 baud:
  SetReferenceVoltage(0x32,0xFF) -> SetFrameRate(0x39,..) -> StartRecording(0x3d)
  -> one byte per frame = 8-bit force.

INSTRUCTIONS: replug, then run this and for the full ~20 s, firmly press the round
sensing dot at the tip of the film and release, over and over (~once per second).
Output is a readable per-second summary (no live display).
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402

BAUD = 1_000_000
RUN_SECS = 20.0


def main():
    print("PRESS-PUMP capture: pump the sensor for ~20 s, then read the trace below.")
    print("=" * 70)
    h = TekscanHandle()
    f = h.ftdi
    f.set_baudrate(BAUD); time.sleep(0.01)
    samples = []
    try:
        f.purge_buffers(); time.sleep(0.003)
        f.write_data(bytes([0x32, 0xFF])); time.sleep(0.1); f.read_data_bytes(16, attempt=2)
        f.write_data(bytes([0x39, 0x30, 0x48, 0xea])); time.sleep(0.15); f.read_data_bytes(16, attempt=2)
        f.write_data(bytes([0x3d]))
        t0 = time.time()
        # collect for RUN_SECS, bucket by second
        buckets = {}
        while time.time() - t0 < RUN_SECS:
            d = f.read_data_bytes(256, attempt=2)
            if d:
                sec = int(time.time() - t0)
                for b in d:
                    samples.append((round(time.time() - t0, 3), b))
                    buckets.setdefault(sec, []).append(b)
        print("\n  per-second force (one byte per frame, ~10 frames/sec):\n")
        print("   sec | min  max  mean | values this second")
        print("   ----+----------------+" + "-" * 40)
        for sec in sorted(buckets):
            vs = buckets[sec]
            mn, mx, me = min(vs), max(vs), sum(vs) / len(vs)
            flag = "  <-- FORCE!" if mx > 5 else ""
            print(f"   {sec:3} | {mn:3}  {mx:3}  {me:5.1f} | {vs[:12]}{flag}")
        allv = [v for _, v in samples]
        peak = max(allv) if allv else 0
        print(f"\n  TOTAL {len(allv)} frames.  overall peak = {peak}")
        if peak > 5:
            print("  ✅✅✅ FORCE REGISTERS — the value pulsed with your presses. SOLVED. 🎉")
        else:
            print("  Stayed flat (peak<=5) even while pumping. Likely the active sensor")
            print("  channel isn't channel 0, or the film isn't seated/contacting. We'll")
            print("  try channel selection next.")
    finally:
        log_trial("press_pump", {"baud": BAUD, "samples": samples,
                  "peak": max((v for _, v in samples), default=0)}, meta={"phase": "press-pump"})
        h.close()
        print()


if __name__ == "__main__":
    main()

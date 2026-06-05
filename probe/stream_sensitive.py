#!/usr/bin/env python3
"""
stream_sensitive.py — set sensitivity (reference voltage) high, THEN stream.

The live stream works (clean ~10 Hz single-byte frames) but force read ~0 because
the handle's reference voltage / gain defaults low. SetReferenceVoltage (opcode
0x32, payload = 1 byte Vref 0-255, from FUN_0045eb90) raises the gain.

Full decoded sequence @ 1,000,000 baud:
  SetReferenceVoltage(0x32, Vref) -> SetFrameRate(0x39,...) -> StartRecording(0x3d)
  -> stream one byte per frame = 8-bit force (no-load 0, rises with force).

Usage:  python probe/stream_sensitive.py [vref_hex]   (default ff = max gain)
Run after a FRESH REPLUG, then press the pad when prompted.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402

GOOD_BAUD = 1_000_000
VREF = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0xFF
SETVREF = bytes([0x32, VREF & 0xFF])
SETRATE_8 = bytes([0x39, 0x30, 0x48, 0xea])
START = bytes([0x3d])
RUN_SECS = 25.0


def main():
    print(f"LIVE FORCE @ 1 Mbaud, Vref=0x{VREF:02x} — press the pad when prompted")
    print("=" * 62)
    h = TekscanHandle()
    f = h.ftdi
    f.set_baudrate(GOOD_BAUD)
    time.sleep(0.01)
    samples = []
    try:
        f.purge_buffers(); time.sleep(0.003)
        f.write_data(SETVREF); time.sleep(0.1)
        a1 = f.read_data_bytes(16, attempt=2)
        print(f"  SetReferenceVoltage {SETVREF.hex()} -> ack {bytes(a1).hex()}")
        f.write_data(SETRATE_8); time.sleep(0.15)
        a2 = f.read_data_bytes(16, attempt=2)
        print(f"  SetFrameRate {SETRATE_8.hex()} -> ack {bytes(a2).hex()}")
        f.write_data(START)
        print("  StartRecording 3d -> streaming.\n  >>> PRESS THE PAD / ADD WEIGHT NOW <<<\n")
        t0 = time.time()
        last, peak = -1, 0
        hb = 0.0
        while time.time() - t0 < RUN_SECS:
            d = f.read_data_bytes(256, attempt=2)
            if d:
                for b in d:
                    samples.append((round(time.time() - t0, 3), b))
                v = d[-1]; peak = max(peak, max(d))
                now = time.time() - t0
                if abs(v - last) >= 2 or now - hb > 1.0:
                    bar = "#" * (peak * 40 // 255)
                    print(f"  t={now:5.1f}s  force={v:3}  peak={peak:3}  |{bar}")
                    last, hb = v, now
        vals = [v for _, v in samples]
        print(f"\n  {len(vals)} frames. no-load≈{min(vals) if vals else '?'}, "
              f"peak={max(vals) if vals else '?'}")
        if vals and max(vals) > 5:
            print(f"  ✅✅✅ LIVE FORCE! value swung 0 -> {max(vals)} under load.")
            print("  TEKSCAN ELF IS READABLE ON LINUX. 🎉  Calibration is the only step left.")
        else:
            print(f"  still flat at Vref=0x{VREF:02x}. Try a different Vref:")
            print("    python probe/stream_sensitive.py 80   (or 40, c0)  after replug.")
    finally:
        log_trial("stream_sensitive", {"baud": GOOD_BAUD, "vref": VREF,
                  "samples": samples, "peak": max((v for _, v in samples), default=0)},
                  meta={"phase": "LIVE-FORCE-sensitivity"})
        h.close()


if __name__ == "__main__":
    main()

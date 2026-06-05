#!/usr/bin/env python3
"""
single_frame.py — capture the ONE measurement frame the handle emits right after
power-up (0xFF wake, then read registers 0x00..0x15). Run once per fresh replug.

  python single_frame.py noload   # save a no-load frame
  python single_frame.py loaded   # capture loaded frame, diff vs no-load baseline
"""
import sys, json, os, time
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan")
Ftdi.add_custom_product(VID, PID, "elf")
label = sys.argv[1] if len(sys.argv) > 1 else "frame"
BASELINE = "/tmp/tek_noload_good.json"

f = Ftdi(); f.open(vendor=VID, product=PID)
try: f.set_bitmode(0x00, Ftdi.BitMode.RESET)
except Exception: pass
f.set_baudrate(115200)
try: f.set_latency_timer(1)
except Exception: pass
f.set_dtr(True); f.set_rts(True)

def rd(secs):
    buf = bytearray(); t0 = time.time()
    while time.time() - t0 < secs:
        d = f.read_data_bytes(4096, attempt=2)
        if d: buf += d
    return bytes(buf)

def cmd(b, secs=0.2):
    f.purge_buffers(); f.write_data(bytes([b])); return rd(secs)

# capture the post-power-up frame (retry the wake a couple times if needed)
frame = {}
for attempt in range(3):
    cmd(0xff, 0.8)                              # wake / trigger
    frame = {f"{c:02x}": cmd(c).hex() for c in range(0x00, 0x16)}
    if sum(1 for v in frame.values() if v) >= 10:
        break
f.close()

got = sum(1 for v in frame.values() if v)
print(f"frame ({got}/22 channels): " + "  ".join(f"{k}={v or '-'}" for k, v in frame.items()))
if got < 10:
    print(">>> MISSED THE ONE-SHOT WINDOW. Unplug/replug the handle and run again.")
    sys.exit(2)

json.dump(frame, open(f"/tmp/tek_{label}.json", "w"))
print(f"saved -> /tmp/tek_{label}.json")

if label == "noload":
    json.dump(frame, open(BASELINE, "w"))
    print(f"baseline updated -> {BASELINE}")
elif label == "loaded" and os.path.exists(BASELINE):
    base = json.load(open(BASELINE))
    print("\n=== CHANGES vs no-load (force channel = the one that moved) ===")
    moved = [(k, base.get(k), frame[k]) for k in frame if base.get(k) != frame[k]]
    if moved:
        for k, b, n in moved:
            print(f"  reg {k}:  no-load={b}  ->  LOADED={n}")
    else:
        print("  (no change — weight may not be centered on the pad, or wrong reg set)")

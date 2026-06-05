#!/usr/bin/env python3
"""
frame_read.py — hypothesis: 0xFF triggers a measurement, then 0x00..0x15 read the
latched registers once. Re-trigger each cycle. Verify we can pull fresh frames
repeatedly, and (optionally) save a baseline for the load comparison.

  python frame_read.py            # print 6 cycles
  python frame_read.py save FILE  # save 6 averaged frames as JSON to FILE
"""
import sys, json, time
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan")
Ftdi.add_custom_product(VID, PID, "elf")
CH = list(range(0x00, 0x16))

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

def cmd(b, secs=0.06):
    f.purge_buffers(); f.write_data(bytes([b])); return rd(secs)

def frame():
    cmd(0xff, 0.05)                       # trigger a fresh measurement
    return {c: cmd(c).hex() for c in CH}

frames = []
for i in range(6):
    fr = frame()
    frames.append(fr)
    print(f"cycle{i}: " + "  ".join(f"{c:02x}={fr[c] or '-'}" for c in CH))
f.close()

if len(sys.argv) > 2 and sys.argv[1] == "save":
    json.dump(frames, open(sys.argv[2], "w"))
    print("saved ->", sys.argv[2])

#!/usr/bin/env python3
"""
gentle_probe.py — replicate the exact setup that previously got structured replies
(open, 115200, DTR/RTS asserted, NO chip reset / NO line pulse) and read only the
safe command range 0x00..0x15 across several passes to check reproducibility.
"""
import time
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan")
Ftdi.add_custom_product(VID, PID, "elf")

f = Ftdi(); f.open(vendor=VID, product=PID)
try: f.set_bitmode(0x00, Ftdi.BitMode.RESET)
except Exception: pass
f.set_baudrate(115200)
try: f.set_latency_timer(1)
except Exception: pass
f.set_dtr(True); f.set_rts(True)

def cmd(b, secs=0.2):
    f.purge_buffers()
    f.write_data(bytes([b]))
    buf = bytearray(); t0 = time.time()
    while time.time() - t0 < secs:
        d = f.read_data_bytes(4096, attempt=2)
        if d: buf += d
    return bytes(buf)

print("ping 0xff ->", cmd(0xff, 1.0).hex() or "(nothing)")
for p in range(4):
    row = []
    for c in range(0x00, 0x16):
        r = cmd(c)
        row.append(f"{c:02x}={r.hex() or '-'}")
    print(f"pass{p}: " + "  ".join(row))
f.close()

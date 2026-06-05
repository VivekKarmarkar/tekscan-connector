#!/usr/bin/env python3
"""
probe_session.py — establish a DETERMINISTIC session with the handle, then verify
that the per-command responses repeat across passes (a prerequisite for the
load test). Clean reset -> DTR/RTS pulse -> wake -> read 0x00..0x15, 3 passes.
"""
import time
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan")
Ftdi.add_custom_product(VID, PID, "elf")

f = Ftdi(); f.open(vendor=VID, product=PID)
try: f.reset()                                   # reset the FTDI chip
except Exception as e: print("reset:", e)
try: f.set_bitmode(0x00, Ftdi.BitMode.RESET)
except Exception: pass
f.set_baudrate(115200)
try: f.set_latency_timer(1)
except Exception: pass
# pulse the control lines to reset the handle's microcontroller, then assert
f.set_dtr(False); f.set_rts(False); time.sleep(0.2)
f.set_dtr(True);  f.set_rts(True);  time.sleep(0.2)
f.purge_buffers()

def cmd(b, secs=0.15):
    f.purge_buffers()
    f.write_data(bytes([b]))
    buf = bytearray(); t0 = time.time()
    while time.time() - t0 < secs:
        d = f.read_data_bytes(64, attempt=2)
        if d: buf += d
    return bytes(buf)

print("wake 0xff ->", cmd(0xff).hex() or "(nothing)")
for p in range(3):
    row = []
    for c in range(0x00, 0x16):
        r = cmd(c)
        row.append(f"{c:02x}={r.hex() or '-'}")
    print(f"pass{p}: " + "  ".join(row))
f.close()

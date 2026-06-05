#!/usr/bin/env python3
"""
baud_sweep.py — the handle (FT232R UART, D2XX) is silent until opened with the
right serial settings. Sweep candidate baud rates with DTR/RTS asserted (like a
COM-port open) and report any baud that produces a byte stream.

Read-only: we never write to the device here.
"""
import sys, time
from collections import Counter
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
BAUDS = [9600, 19200, 38400, 57600, 115200, 230400, 460800,
         921600, 1000000, 1500000, 2000000, 3000000]

Ftdi.add_custom_vendor(VID, "tekscan")
Ftdi.add_custom_product(VID, PID, "elf")

def try_baud(baud, secs=1.0):
    f = Ftdi()
    f.open(vendor=VID, product=PID)
    try: f.set_bitmode(0x00, Ftdi.BitMode.RESET)
    except Exception: pass
    f.set_baudrate(baud)
    try: f.set_latency_timer(2)
    except Exception: pass
    for dtr, rts in ((True, True),):          # assert modem lines, like a port open
        try:
            f.set_dtr(dtr); f.set_rts(rts)
        except Exception: pass
    f.purge_buffers()
    time.sleep(0.1)
    buf = bytearray()
    t0 = time.time()
    while time.time() - t0 < secs:
        d = f.read_data_bytes(4096, attempt=2)
        if d: buf += d
    f.close()
    return bytes(buf)

def main():
    print(f"chip sweep on {VID:#06x}:{PID:#06x}")
    hits = []
    for b in BAUDS:
        data = try_baud(b)
        tag = ""
        if data:
            h = Counter(data)
            tag = f"  distinct={len(h)} top={h.most_common(3)} first={data[:24].hex(' ')}"
            hits.append((b, len(data)))
        print(f"  baud {b:>8}: {len(data):>6} bytes{tag}")
    print("\nstreaming bauds:", hits or "(none — handle needs a start command, not just a baud)")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
explore_115200.py — the handle speaks at 115200 and acked 0xFF. Map its command
set: send every single-byte command, log which ones respond, and characterize
any command that produces a continuous (streaming) response = the 'start' command.
"""
import time
from collections import Counter
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

def read_for(secs):
    buf = bytearray(); t0 = time.time()
    while time.time() - t0 < secs:
        d = f.read_data_bytes(4096, attempt=2)
        if d: buf += d
    return bytes(buf)

# 1) ping 0xFF with a long read — does the ack turn into a stream?
f.purge_buffers(); f.write_data(b"\xff")
r = read_for(2.0)
print(f"ping 0xff -> {len(r)} bytes: {r[:64].hex(' ')}")

# 2) full single-byte command sweep
print("== single-byte command sweep @115200 (DTR/RTS asserted) ==")
hits, big = [], None
for c in range(256):
    f.purge_buffers()
    f.write_data(bytes([c]))
    r = read_for(0.2)
    if r:
        hits.append((c, len(r)))
        if not (len(r) == 1 and r[0] == 0xff):           # show anything non-trivial
            print(f"  cmd {c:02x} -> {len(r)} bytes  {r[:32].hex(' ')}")
        if len(r) > 40 and big is None:
            big = c
print("responsive cmds:", ", ".join(f"{c:02x}({n})" for c, n in hits) or "(none)")

# 3) characterize a streaming command if found
if big is not None:
    print(f"== streaming candidate cmd {big:02x} — capturing 2s ==")
    f.purge_buffers(); f.write_data(bytes([big]))
    r = read_for(2.0)
    h = Counter(r)
    print(f"  {len(r)} bytes, distinct={len(h)}, top={h.most_common(6)}")
    print(f"  first 96: {r[:96].hex(' ')}")
    try: f.write_data(b"\xfe")   # guess: 0xFE = stop (mirror of 0xFF), be polite
    except Exception: pass

f.close()

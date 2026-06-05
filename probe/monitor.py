#!/usr/bin/env python3
"""
monitor.py — continuously read the candidate registers for ~14s while the user
presses/releases the sensor pad. Reports the value RANGE per register; any
register whose range spans (moves off 255) is the force channel. Timing-proof:
no need to sync the press with a single read.
"""
import time
from collections import defaultdict
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan"); Ftdi.add_custom_product(VID, PID, "elf")
REGS = [0x70, 0x63, 0x3e, 0x33, 0x3c, 0x44, 0x61, 0x05]

f = Ftdi(); f.open(vendor=VID, product=PID)
def rd(s):
    b = bytearray(); t = time.time()
    while time.time() - t < s:
        d = f.read_data_bytes(64, attempt=2)
        if d: b += d
    return bytes(b)
def init():
    f.set_bitmode(0x80, Ftdi.BitMode.CBUS); f.set_baudrate(750000)
    f.set_line_property(8, 1, 'N'); f.set_latency_timer(2)
    time.sleep(0.02); f.set_bitmode(0x88, Ftdi.BitMode.CBUS)
    time.sleep(0.02); f.set_bitmode(0x00, Ftdi.BitMode.RESET)
    f.purge_buffers(); time.sleep(0.04)
def value(c):
    f.purge_buffers(); time.sleep(0.002); f.write_data(bytes([c])); r = rd(0.025)
    for i in range(len(r) - 1):
        if (r[i] ^ r[i+1]) == 0xFF: return r[i]
    return None

init()
seen = defaultdict(set)
print("MONITORING 16s — press AND release the round pad a few times now...")
t0 = time.time(); n = 0; got = 0
while time.time() - t0 < 16:
    for c in REGS:
        v = value(c)
        if v is not None: seen[c].add(v); got += 1
    n += 1
    if n % 12 == 0: init()        # periodic re-init to avoid wedging
f.close()
print(f"\n{n} sweeps. value ranges seen per register:")
moved = []
for c in REGS:
    vs = sorted(seen[c])
    rng = (max(vs) - min(vs)) if vs else 0
    flag = "  <== MOVES! (force channel)" if rng > 3 else ""
    print(f"  reg 0x{c:02x}: seen {vs[:8]}{'...' if len(vs)>8 else ''}  range={rng}{flag}")
    if rng > 3: moved.append(c)
print("\nforce channel(s):", [hex(c) for c in moved] or "none moved — check sensor seating / press the round pad")

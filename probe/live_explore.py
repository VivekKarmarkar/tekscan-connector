#!/usr/bin/env python3
"""
live_explore.py — autonomous (no-load) hunt for the sensor-read / scan command.
The device is stable at 750000 8N1 after a CBUS3 reset; single bytes return idle
'00 ff' (0xFF = not-ready). Look for any command that returns a STRUCTURED frame
or 'arms' a real (non-0xFF) reading. Re-init (CBUS reset) between phases.
"""
import time
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan"); Ftdi.add_custom_product(VID, PID, "elf")

def init(f):
    f.set_bitmode(0x80, Ftdi.BitMode.CBUS); f.set_baudrate(750000); f.set_line_property(8, 1, 'N')
    try: f.set_latency_timer(2)
    except Exception: pass
    time.sleep(0.03); f.set_bitmode(0x88, Ftdi.BitMode.CBUS)
    time.sleep(0.03); f.set_bitmode(0x00, Ftdi.BitMode.RESET)
    f.purge_buffers(); time.sleep(0.05)

f = Ftdi(); f.open(vendor=VID, product=PID); init(f)
def rd(s):
    b = bytearray(); t = time.time()
    while time.time() - t < s:
        d = f.read_data_bytes(4096, attempt=3)
        if d: b += d
    return bytes(b)
def cmd(data, s=0.05):
    f.purge_buffers(); f.write_data(bytes(data)); return rd(s)

IDLE = b'\x00\xff'

print("=== A: full single-byte sweep @750000 (non-idle responses) ===")
hits = []
for c in range(256):
    r = cmd([c])
    if r and r != IDLE:
        hits.append((c, r)); print(f"  cmd {c:02x} -> {len(r)}B: {r.hex(' ')}")
    if c % 32 == 31: init(f)
print(f"  non-idle single bytes: {[(hex(c), r.hex()) for c, r in hits] or 'none'}")
init(f)

print("=== B: long read (0.6s) after selected commands ===")
for c in [0x00, 0x05, 0x10, 0x20, 0x40, 0x80, 0xa0, 0xc0, 0xe0, 0xf0, 0xfe]:
    r = cmd([c], 0.6)
    print(f"  cmd {c:02x} -> {len(r)}B: {r[:48].hex(' ')}")
init(f)

print("=== C: 2-byte commands (non-idle) ===")
for hi in [0x00, 0x01, 0x02, 0x10, 0x55, 0x80, 0xaa, 0xf0, 0xfe]:
    for lo in [0x00, 0x01, 0x06, 0x55, 0xaa, 0xff]:
        r = cmd([hi, lo])
        if r and r != IDLE:
            print(f"  cmd {hi:02x} {lo:02x} -> {len(r)}B: {r.hex(' ')}")
init(f)

print("=== D: arming test — send X, then read 0x05 (look for non-idle) ===")
for x in range(256):
    cmd([x], 0.02)
    r = cmd([0x05], 0.04)
    if r and r != IDLE:
        print(f"  after {x:02x}: read(0x05) -> {r.hex(' ')}")
    if x % 32 == 31: init(f)
f.close()
print("done")

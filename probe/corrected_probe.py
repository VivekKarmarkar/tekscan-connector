#!/usr/bin/env python3
"""
corrected_probe.py — init the handle the way ElfMPort.exe actually does it
(recovered from the binary): CBUS3 reset pulse via FTDI CBUS bit-bang, then
750000 baud, 8N1. Then see if it streams / responds with live data.
"""
import time
from collections import Counter
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan")
Ftdi.add_custom_product(VID, PID, "elf")

f = Ftdi(); f.open(vendor=VID, product=PID)

def read_for(secs):
    buf = bytearray(); t0 = time.time()
    while time.time() - t0 < secs:
        d = f.read_data_bytes(4096, attempt=3)
        if d: buf += d
    return bytes(buf)

# --- init recovered from ElfMPort.exe ---
# CBUS bit-bang: high nibble = direction (1=out), low nibble = value. CBUS3.
f.set_bitmode(0x80, Ftdi.BitMode.CBUS)     # CBUS3 output, LOW  (reset asserted)
f.set_baudrate(750000)
f.set_line_property(8, 1, 'N')             # 8N1
try: f.set_latency_timer(2)
except Exception: pass
time.sleep(0.05)
f.set_bitmode(0x88, Ftdi.BitMode.CBUS)     # CBUS3 output, HIGH (reset released)
time.sleep(0.05)
f.set_bitmode(0x00, Ftdi.BitMode.RESET)    # back to UART
f.purge_buffers()
time.sleep(0.1)

print("=== unsolicited stream after correct init (2s @750000 8N1) ===")
d = read_for(2.0); h = Counter(d)
print(f"  {len(d)} bytes  distinct={len(h)}  top={h.most_common(6)}")
print(f"  first 64: {d[:64].hex(' ')}")

print("=== commands at 750000 ===")
def cmd(b, secs=0.15):
    f.purge_buffers(); f.write_data(bytes([b])); return read_for(secs)
for c in [0xff, 0x00, 0x01, 0x05, 0x09, 0x11, 0x13]:
    r = cmd(c)
    print(f"  cmd {c:02x} -> {len(r):4d} bytes: {r[:32].hex(' ')}")
f.close()

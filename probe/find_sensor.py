#!/usr/bin/env python3
"""
find_sensor.py — with the decoded protocol, sweep all registers and find the one
whose 8-bit value moves under load (the force channel). Robust [value][~value]
parser (scans the reply for the first valid checksummed pair).

  baseline -> read all regs at NO load, save
  loaded   -> read under load, diff (sensor = biggest drop from its no-load value)
"""
import sys, json, time
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan"); Ftdi.add_custom_product(VID, PID, "elf")
mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
BASE = "/tmp/tek_sensor_base.json"

f = Ftdi(); f.open(vendor=VID, product=PID)
def rd(s):
    b = bytearray(); t = time.time()
    while time.time() - t < s:
        d = f.read_data_bytes(256, attempt=3)
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
    for i in range(len(r) - 1):                       # robust [v][~v] scan
        if (r[i] ^ r[i+1]) == 0xFF: return r[i]
    return None

init()
alive = sum(1 for c in range(0x40, 0x80) if value(c) is not None)
print(f"alive check: {alive}/64 registers responded in 0x40-0x7f"
      + ("  -> device OK" if alive else "  -> NO RESPONSE (replug again?)"))
m = {}
for c in range(256):
    v = value(c)
    if v is not None: m[f"{c:02x}"] = v
    if c % 32 == 31: init()
print(f"registers responding: {len(m)}")
f.close()

if mode == "baseline":
    json.dump(m, open(BASE, "w"))
    print("baseline saved. non-zero registers (force candidates):")
    print("  " + ", ".join(f"{k}={v}" for k, v in m.items() if v not in (0,)))
else:
    base = json.load(open(BASE))
    changed = [(k, base.get(k), m[k]) for k in m if base.get(k) != m[k]]
    changed.sort(key=lambda x: (x[1] or 0) - (x[2] or 0), reverse=True)
    print("\n=== registers that CHANGED under load (sensor = biggest drop) ===")
    for k, b, n in changed[:15]:
        print(f"  reg 0x{k}: {b} -> {n}   (drop {(b or 0)-(n or 0)})")
    if not changed:
        print("  (nothing changed — press harder / hold during the read)")

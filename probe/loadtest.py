#!/usr/bin/env python3
"""
loadtest.py — with the CORRECT init (CBUS3 reset + 750000 8N1), the device is
stable, so we can diff no-load vs loaded in one session (no replug needed).

  baseline -> read 0x00..0x15 (x5 each), save
  loaded   -> read again, diff (force channel = the value that dropped from 0xff)
"""
import sys, json, time
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan"); Ftdi.add_custom_product(VID, PID, "elf")
mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"

f = Ftdi(); f.open(vendor=VID, product=PID)
def read_for(s):
    b = bytearray(); t = time.time()
    while time.time() - t < s:
        d = f.read_data_bytes(4096, attempt=3)
        if d: b += d
    return bytes(b)

# init recovered from ElfMPort.exe
f.set_bitmode(0x80, Ftdi.BitMode.CBUS); f.set_baudrate(750000); f.set_line_property(8, 1, 'N')
try: f.set_latency_timer(2)
except Exception: pass
time.sleep(0.05); f.set_bitmode(0x88, Ftdi.BitMode.CBUS)
time.sleep(0.05); f.set_bitmode(0x00, Ftdi.BitMode.RESET)
f.purge_buffers(); time.sleep(0.1)

def cmd(c, s=0.06):
    f.purge_buffers(); f.write_data(bytes([c])); return read_for(s)

res = {f"{c:02x}": [cmd(c).hex() for _ in range(5)] for c in range(0x00, 0x16)}
f.close()
for c, v in res.items():
    print(f"  {c}: {v}")

BASE = "/tmp/tek_corr_base.json"
if mode == "baseline":
    json.dump(res, open(BASE, "w")); print("baseline saved")
else:
    base = json.load(open(BASE))
    print("\n=== CHANGED under load (force channel) ===")
    changed = False
    for c in res:
        if set(base.get(c, [])) != set(res[c]):
            changed = True
            print(f"  reg {c}:  no-load={base.get(c)}  ->  LOADED={res[c]}")
    print("  (no change)" if not changed else "")

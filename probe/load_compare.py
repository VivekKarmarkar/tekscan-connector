#!/usr/bin/env python3
"""
load_compare.py — poll every command at 115200 and record its response, so we can
diff NO-LOAD vs WEIGHT-ON-PAD and find which command reads the force value.

  baseline  -> read all commands, save to /tmp/tek_baseline.json
  compare   -> read all commands, diff against the saved baseline
"""
import sys, json, time
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan")
Ftdi.add_custom_product(VID, PID, "elf")
CMDS = list(range(0x00, 0x20))
mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"

f = Ftdi(); f.open(vendor=VID, product=PID)
try: f.set_bitmode(0x00, Ftdi.BitMode.RESET)
except Exception: pass
f.set_baudrate(115200)
try: f.set_latency_timer(1)
except Exception: pass
f.set_dtr(True); f.set_rts(True)
time.sleep(0.1)

def rd(secs=0.12):
    buf = bytearray(); t0 = time.time()
    while time.time() - t0 < secs:
        d = f.read_data_bytes(256, attempt=2)
        if d: buf += d
    return bytes(buf)

result = {}
for c in CMDS:
    reads = []
    for _ in range(6):
        f.purge_buffers()
        f.write_data(bytes([c]))
        reads.append(rd().hex())
        time.sleep(0.02)
    result[f"{c:02x}"] = reads
f.close()

if mode == "baseline":
    json.dump(result, open("/tmp/tek_baseline.json", "w"))
    print("NO-LOAD baseline saved. responses (6 reads each):")
    for c, rs in result.items():
        print(f"  cmd {c}: {rs}")
else:
    base = json.load(open("/tmp/tek_baseline.json"))
    print("=== commands whose response CHANGED under load ===")
    changed = False
    for c in result:
        if set(base.get(c, [])) != set(result[c]):
            changed = True
            print(f"  cmd {c}:  no-load={base.get(c)}\n           loaded ={result[c]}")
    if not changed:
        print("  (nothing changed — wrong command set, or weight not on the pad)")
    print("\n=== full loaded responses ===")
    for c, rs in result.items():
        print(f"  cmd {c}: {rs}")

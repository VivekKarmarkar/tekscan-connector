#!/usr/bin/env python3
"""
candidate_loadtest.py — test ONLY the narrowed non-idle candidate commands under
load. Because the device is stateful, we always read the candidates in the SAME
fixed sequence after a fresh CBUS reset, so baseline vs loaded is comparable.

  baseline -> read candidates (x6 sequences), save
  loaded   -> read again under load, diff (force cmd = the value that moves)
"""
import sys, json, time
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan"); Ftdi.add_custom_product(VID, PID, "elf")
CANDS = [0x44, 0x61, 0x70, 0x30, 0x3e, 0x62, 0x33, 0x05]   # 0x05 = idle control
mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
BASE = "/tmp/tek_cand_base.json"

f = Ftdi(); f.open(vendor=VID, product=PID)
def init():
    f.set_bitmode(0x80, Ftdi.BitMode.CBUS); f.set_baudrate(750000); f.set_line_property(8, 1, 'N')
    try: f.set_latency_timer(2)
    except Exception: pass
    time.sleep(0.02); f.set_bitmode(0x88, Ftdi.BitMode.CBUS)
    time.sleep(0.02); f.set_bitmode(0x00, Ftdi.BitMode.RESET)
    f.purge_buffers(); time.sleep(0.04)
def rd(s):
    b = bytearray(); t = time.time()
    while time.time() - t < s:
        d = f.read_data_bytes(4096, attempt=3)
        if d: b += d
    return bytes(b)
def one(c):
    f.purge_buffers(); time.sleep(0.003); f.write_data(bytes([c])); time.sleep(0.006); return rd(0.025).hex()

seqs = []
for _ in range(6):
    init()
    seqs.append({f"{c:02x}": one(c) for c in CANDS})
f.close()

# aggregate: per command, the set of values seen across the 6 sequences
agg = {f"{c:02x}": sorted({s[f"{c:02x}"] for s in seqs}) for c in CANDS}
for c, vs in agg.items():
    print(f"  cmd {c}: {vs}")

if mode == "baseline":
    json.dump(agg, open(BASE, "w")); print("baseline saved")
else:
    base = json.load(open(BASE))
    print("\n=== candidates whose value CHANGED under load (= the force command) ===")
    moved = [c for c in agg if set(agg[c]) != set(base.get(c, []))]
    for c in moved:
        print(f"  cmd {c}:  no-load={base.get(c)}  ->  LOADED={agg[c]}")
    print("  (none changed)" if not moved else "")

#!/usr/bin/env python3
"""
wake_attempt.py — the handle is an FT232R UART that stays silent until commanded.
Bounded attempt to wake it without the real protocol:
  (1) DTR reset pulse (low->high) + RTS, per baud  — many micros start on this.
  (2) a few common 'start' bytes, at the most likely bauds.
Read-only otherwise. If nothing here streams, the protocol genuinely needs a
usbmon capture of the Windows ELF software (or binary RE of it).
"""
import time
from collections import Counter
from pyftdi.ftdi import Ftdi

VID, PID = 0x11DA, 0x0012
Ftdi.add_custom_vendor(VID, "tekscan")
Ftdi.add_custom_product(VID, PID, "elf")

def opn(baud):
    f = Ftdi(); f.open(vendor=VID, product=PID)
    try: f.set_bitmode(0x00, Ftdi.BitMode.RESET)
    except Exception: pass
    f.set_baudrate(baud)
    try: f.set_latency_timer(2)
    except Exception: pass
    return f

def read_for(f, secs):
    buf = bytearray(); t0 = time.time()
    while time.time() - t0 < secs:
        d = f.read_data_bytes(4096, attempt=2)
        if d: buf += d
    return bytes(buf)

def summarize(tag, data):
    if data:
        h = Counter(data)
        print(f"  >>> HIT {tag}: {len(data)} bytes  distinct={len(h)} "
              f"top={h.most_common(3)} first={data[:32].hex(' ')}")
        return True
    print(f"      {tag}: 0")
    return False

found = False
print("== (1) DTR reset-pulse wake ==")
for baud in [9600, 19200, 38400, 57600, 115200, 230400, 921600, 1000000]:
    f = opn(baud)
    try:
        f.set_dtr(False); f.set_rts(False); time.sleep(0.05)
        f.set_dtr(True);  f.set_rts(True);  time.sleep(0.05)
        f.purge_buffers()
        found |= summarize(f"baud {baud} dtr-pulse", read_for(f, 0.7))
    finally:
        f.close()

print("== (2) common start-bytes ==")
CMDS = [b"\xff", b"\x02", b"\x01", b"S", b"\r", b"\x11", b"\x55", b"\xaa", b"\x1b", b"?"]
for baud in [115200, 921600, 57600, 230400]:
    for cmd in CMDS:
        f = opn(baud)
        try:
            f.set_dtr(True); f.set_rts(True); f.purge_buffers()
            f.write_data(cmd); time.sleep(0.03)
            found |= summarize(f"baud {baud} cmd={cmd.hex()}", read_for(f, 0.4))
        finally:
            f.close()

print("\nRESULT:", "STREAM FOUND — investigate above" if found
      else "no response — protocol needs a usbmon capture / binary RE of ELF")

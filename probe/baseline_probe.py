#!/usr/bin/env python3
"""
baseline_probe.py — re-establish the known-good single-byte read baseline.

Earlier sessions swept all 256 registers with single-byte reads returning clean
[value][~value] frames (e.g. 00 ff = value 0). Now multi-byte SetFrameRate sends
return c0-framed bytes and wedge the device. Before more protocol theory, confirm
what the PLAIN single-byte read path returns on this handle RIGHT NOW, and how
many reads it survives before wedging.

Run after a FRESH REPLUG. Reads benign registers individually, capturing RAW
bytes, so we see 00ff-style frames vs c0 garbage, and the wedge point.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402


def read_raw(f, reg, secs=0.05):
    f.purge_buffers(); time.sleep(0.002)
    f.write_data(bytes([reg]))
    buf, end = bytearray(), time.time() + secs
    while time.time() < end:
        d = f.read_data_bytes(64, attempt=3)
        if d:
            buf += d
    return bytes(buf)


def main():
    print("Baseline single-byte read probe (run after fresh replug)")
    print("=" * 60)
    h = TekscanHandle()
    f = h.ftdi
    rows = []
    regs = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08]  # repeat to find wedge
    try:
        first_silent = None
        for i, reg in enumerate(regs):
            raw = read_raw(f, reg)
            valid = len(raw) == 2 and (raw[0] ^ raw[1]) == 0xFF
            val = raw[0] if valid else None
            rows.append({"i": i, "reg": reg, "raw": raw.hex(),
                         "valid_frame": valid, "value": val})
            mark = f"value={val}" if valid else ("SILENT" if not raw else "non-frame")
            print(f"  #{i:2} reg 0x{reg:02x} -> {len(raw)}B {raw.hex():8}  {mark}")
            if not raw and first_silent is None:
                first_silent = i
        responded = sum(1 for r in rows if r["raw"])
        framed = sum(1 for r in rows if r["valid_frame"])
        print(f"\n  responded: {responded}/{len(regs)}  valid [v,~v] frames: {framed}")
        print(f"  first silent at: {'#'+str(first_silent) if first_silent is not None else 'never'}")
        if framed >= len(regs) - 2:
            print("  -> HEALTHY: single-byte polling works; wedge is specific to multi-byte cmds.")
        elif responded <= 2:
            print("  -> WEDGES after ~1-2 reads regardless of command -> init/read path issue,")
            print("     OR device only services a brief post-powerup window now.")
        else:
            print("  -> partial; see raw bytes for the framing the device actually uses.")
    finally:
        log_trial("baseline_probe", {"rows": rows}, meta={"phase": "rebaseline"})
        h.close()


if __name__ == "__main__":
    main()

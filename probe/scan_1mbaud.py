#!/usr/bin/env python3
"""
scan_1mbaud.py — full register map at the CORRECT baud (1,000,000).

The baud sweep proved the handle speaks clean [value][~value] frames at 1 Mbaud
(not the 750000 we'd been using). Map every register 0x00-0x7f at no load so we
can spot the live-force channel (low at no-load, will rise under force).
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402

GOOD_BAUD = 1_000_000


def poll(f, reg, secs=0.04):
    f.purge_buffers(); time.sleep(0.002)
    f.write_data(bytes([reg]))
    buf, end = bytearray(), time.time() + secs
    while time.time() < end:
        d = f.read_data_bytes(64, attempt=3)
        if d:
            buf += d
    return bytes(buf)


def main():
    print("Full register map @ 1,000,000 baud (no load)")
    print("=" * 60)
    h = TekscanHandle()
    f = h.ftdi
    f.set_baudrate(GOOD_BAUD)
    time.sleep(0.01)
    rows = {}
    try:
        for reg in range(0x00, 0x80):
            raw = poll(f, reg)
            if len(raw) == 2 and (raw[0] ^ raw[1]) == 0xFF:
                rows[reg] = raw[0]
        # print clean registers grouped
        print(f"  {len(rows)} registers returned clean frames:\n")
        line = []
        for reg in sorted(rows):
            line.append(f"0x{reg:02x}={rows[reg]:3}")
            if len(line) == 6:
                print("   " + "  ".join(line)); line = []
        if line:
            print("   " + "  ".join(line))
        # candidates = registers reading a LOW value (no-load force ~0, rises w/ force)
        lows = {r: v for r, v in rows.items() if v <= 8}
        highs = {r: v for r, v in rows.items() if v >= 250}
        mids = {r: v for r, v in rows.items() if 8 < v < 250}
        print(f"\n  low (<=8, no-load force candidates): "
              f"{', '.join(f'0x{r:02x}={v}' for r,v in sorted(lows.items()))}")
        print(f"  mid (8-250): {', '.join(f'0x{r:02x}={v}' for r,v in sorted(mids.items())) or '(none)'}")
        print(f"  high (>=250): {', '.join(f'0x{r:02x}={v}' for r,v in sorted(highs.items()))}")
        print("\n  Next: monitor these while you press the pad — the live force register MOVES.")
    finally:
        log_trial("scan_1mbaud", {"baud": GOOD_BAUD,
                  "registers": {f"0x{r:02x}": v for r, v in rows.items()}},
                  meta={"phase": "1mbaud-map", "load": "none"})
        h.close()


if __name__ == "__main__":
    main()

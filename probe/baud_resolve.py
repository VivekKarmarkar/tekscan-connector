#!/usr/bin/env python3
"""
baud_resolve.py — find the baud where single-byte reads return clean
[value][~value] frames (byte1 == ~byte0). The baseline probe returned
0x80/0xc0/0xe0/0xf0 with zeroed low bits = classic baud-mismatch fingerprint.

Single-byte reads do NOT wedge the device, so we can sweep baud in one session
without replugging. For each baud, poll a few registers and score how many
responses are valid complement frames.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402

BAUDS = [9600, 19200, 38400, 57600, 115200, 230400, 250000, 460800,
         500000, 750000, 921600, 1000000, 1500000, 2000000, 3000000]
REGS = [0x05, 0x06, 0x44, 0x61]


def poll(f, reg, secs=0.05):
    f.purge_buffers(); time.sleep(0.002)
    f.write_data(bytes([reg]))
    buf, end = bytearray(), time.time() + secs
    while time.time() < end:
        d = f.read_data_bytes(64, attempt=3)
        if d:
            buf += d
    return bytes(buf)


def main():
    print("Baud sweep — looking for clean [value][~value] frames")
    print("=" * 60)
    h = TekscanHandle()
    f = h.ftdi
    results = []
    try:
        for baud in BAUDS:
            try:
                f.set_baudrate(baud)
            except Exception as e:
                print(f"  baud {baud:>8}: set failed ({e})")
                continue
            time.sleep(0.01)
            clean = 0
            samples = []
            for reg in REGS:
                raw = poll(f, reg)
                samples.append(raw.hex())
                if len(raw) == 2 and (raw[0] ^ raw[1]) == 0xFF:
                    clean += 1
            tag = "  <<< CLEAN FRAMES" if clean >= 2 else ""
            print(f"  baud {baud:>8}: {clean}/{len(REGS)} clean  samples={samples}{tag}")
            results.append({"baud": baud, "clean": clean, "samples": samples})
        best = max(results, key=lambda r: r["clean"]) if results else None
        print()
        if best and best["clean"] >= 2:
            print(f"  ✅ BEST baud = {best['baud']} ({best['clean']}/{len(REGS)} clean frames)")
            print("     Re-test the start sequence at this baud.")
        else:
            print("  ❌ No baud produced clean complement frames.")
            print("     The c0/80 pattern may not be baud — could be a 9-bit/parity or")
            print("     framing scheme. See samples per baud in probe/results/.")
    finally:
        log_trial("baud_resolve", {"results": results}, meta={"phase": "baud-sweep"})
        h.close()


if __name__ == "__main__":
    main()

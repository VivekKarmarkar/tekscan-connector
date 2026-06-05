#!/usr/bin/env python3
"""
monitor_press.py — find the live FORCE register by watching which one moves
while you press the pad. Runs at the correct 1,000,000 baud.

Baselines every clean register (all ~0 at no load), then for ~25 s re-reads them
and reports any register whose value departs from its baseline. Press the sensor
pad / add the weight during the window — the live force channel will climb while
the others stay flat.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402

GOOD_BAUD = 1_000_000
# clean registers from the no-load map (skip 0x44=FWversion). Watch 0x01..0x43.
REGS = [r for r in range(0x01, 0x44) if r not in (0x44,)]
DURATION = 25.0
THRESH = 4


def poll(f, reg, secs=0.015):
    f.purge_buffers(); time.sleep(0.0015)
    f.write_data(bytes([reg]))
    buf, end = bytearray(), time.time() + secs
    while time.time() < end:
        d = f.read_data_bytes(64, attempt=2)
        if d:
            buf += d
    if len(buf) >= 2 and (buf[0] ^ buf[1]) == 0xFF:
        return buf[0]
    return None


def main():
    print("LIVE FORCE FINDER @ 1 Mbaud")
    print("=" * 60)
    h = TekscanHandle()
    f = h.ftdi
    f.set_baudrate(GOOD_BAUD)
    time.sleep(0.01)
    moved = {}
    try:
        base = {}
        for r in REGS:
            base[r] = poll(f, r) or 0
        print(f"  baselined {len(base)} registers (all ~{max(base.values())} max at no load)")
        print(f"\n  >>> PRESS THE PAD HARD NOW — and keep pressing for {int(DURATION)} s <<<\n")
        t0 = time.time()
        peak_reg, peak_val = None, 0
        while time.time() - t0 < DURATION:
            for r in REGS:
                v = poll(f, r)
                if v is None:
                    continue
                d = abs(v - base[r])
                if d >= THRESH:
                    moved[r] = max(moved.get(r, 0), v)
                    if v > peak_val:
                        peak_val, peak_reg = v, r
                        print(f"  t={time.time()-t0:5.1f}s  reg 0x{r:02x}: {base[r]} -> {v}  "
                              f"(Δ{v-base[r]})  <-- MOVING")
        print()
        if moved:
            top = sorted(moved.items(), key=lambda kv: -kv[1])
            print("  ✅ REGISTERS THAT MOVED UNDER FORCE:")
            for r, v in top:
                print(f"     reg 0x{r:02x}: no-load {base[r]} -> peak {v}")
            print(f"\n  🎯 LIVE FORCE REGISTER = 0x{top[0][0]:02x} (peak {top[0][1]})")
            print("     This is the sensor channel. We can now calibrate force = a*value + b.")
        else:
            print("  No register moved. Either the press wasn't on the active pad, the")
            print("  sensor channel is >0x43, or a scan/enable command is still needed.")
            print("  (All raw data logged to probe/results/.)")
    finally:
        log_trial("monitor_press", {"baud": GOOD_BAUD, "baseline": base,
                  "moved": moved}, meta={"phase": "find-force-register"})
        h.close()


if __name__ == "__main__":
    main()

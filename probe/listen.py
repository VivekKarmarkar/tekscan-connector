#!/usr/bin/env python3
"""
listen.py — after SetFrameRate, listen a long time with timestamps.

Resolves: is the device ARMED-AND-WAITING (ack only, no further bytes) or
STREAMING-TOO-SLOWLY (frames trickle in because the period was mis-decoded)?

Run right after a FRESH REPLUG. Sends only SetFrameRate (no GetFWversion first,
to not spend the device's responsiveness), then listens 15 s and prints every
byte burst with the time it arrived. If bytes keep coming -> it's streaming
(maybe slow). If only the ack -> it's waiting for a separate start/trigger.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402

CMD = bytes([0x39, 0x50, 0x15, 0xff])   # SetFrameRate @100Hz (decoded)


def main():
    print("Listen-after-SetFrameRate (run right after a fresh replug)")
    print("=" * 60)
    h = TekscanHandle()
    f = h.ftdi
    bursts = []
    try:
        f.purge_buffers(); time.sleep(0.003)
        t0 = time.time()
        f.write_data(CMD)
        print(f"  sent {CMD.hex()} at t=0.000")
        last_report = 0
        while time.time() - t0 < 15.0:
            d = f.read_data_bytes(256, attempt=2)
            if d:
                t = time.time() - t0
                bursts.append((round(t, 3), bytes(d).hex()))
                print(f"  t={t:6.3f}s  +{len(d):3}B  {bytes(d).hex()}")
            else:
                # heartbeat so the user sees it's alive
                el = time.time() - t0
                if int(el) > last_report:
                    last_report = int(el)
                    if last_report % 3 == 0:
                        print(f"  …{last_report}s (silent)")
        total = sum(len(bytes.fromhex(b)) for _, b in bursts)
        print(f"\n  total: {len(bursts)} bursts, {total} bytes over 15 s")
        if len(bursts) <= 1:
            print("  -> ACK ONLY: device armed/waiting; needs a separate start/trigger (try 0x3d next).")
        elif total > 30:
            print("  -> STREAMING: bytes kept coming. Check rate; parse [value][~value].")
        else:
            print("  -> TRICKLE: a few late bytes; likely slow stream from mis-decoded period.")
    finally:
        log_trial("listen_after_setrate", {"cmd": CMD.hex(), "bursts": bursts},
                  meta={"phase": "long-listen"})
        h.close()


if __name__ == "__main__":
    main()

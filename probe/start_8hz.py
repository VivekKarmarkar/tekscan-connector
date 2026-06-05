#!/usr/bin/env python3
"""
start_8hz.py — test the 0xFF-wedge hypothesis + clean start at 8 Hz.

OBSERVATION: every time the device went dead, the last byte I'd sent was 0xFF
(the 100 Hz SetFrameRate command is `39 50 15 ff`). 0xFF is the device's known
"not-ready/reset" sentinel — sending it likely wedges the handle. The 8 Hz
command `39 30 48 ea` contains NO 0xFF.

Sequence (fresh replug): init -> SetFrameRate(8Hz, no FF) -> ack -> probe whether
device is STILL ALIVE (send 0x3d StartRecording, then a benign 0x05 read) ->
listen. If the device keeps responding (didn't wedge), the 0xFF hypothesis holds
and we can iterate toward a stream.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402

SETRATE_8 = bytes([0x39, 0x30, 0x48, 0xea])   # SetFrameRate @8Hz (NO 0xFF)
START = bytes([0x3d])


def read_for(f, secs):
    buf, end = bytearray(), time.time() + secs
    while time.time() < end:
        d = f.read_data_bytes(256, attempt=2)
        if d:
            buf += d
    return bytes(buf)


def main():
    print("8 Hz start test (no 0xFF in command) — tests the wedge hypothesis")
    print("=" * 64)
    h = TekscanHandle()
    f = h.ftdi
    log = {}
    try:
        f.purge_buffers(); time.sleep(0.003)
        t0 = time.time()
        f.write_data(SETRATE_8)
        r1 = read_for(f, 0.6)
        log["setrate"] = r1.hex()
        print(f"  SetFrameRate 39 30 48 ea -> {len(r1)}B  {r1.hex()}")

        f.write_data(START)
        r2 = read_for(f, 3.0)
        log["startrec"] = r2.hex()
        print(f"  StartRecording 0x3d      -> {len(r2)}B  {r2.hex()}")

        # ALIVE CHECK: if device still answers a benign read, it did NOT wedge.
        f.purge_buffers(); time.sleep(0.002)
        f.write_data(bytes([0x05]))
        r3 = read_for(f, 0.3)
        log["alive_0x05"] = r3.hex()
        print(f"  alive-check 0x05         -> {len(r3)}B  {r3.hex()}")

        # one more listen for a delayed stream
        r4 = read_for(f, 8.0)
        log["listen"] = r4.hex()
        print(f"  long listen              -> {len(r4)}B  {r4.hex()[:120]}")

        alive = len(r3) > 0 or len(r2) > 0
        print(f"\n  device still responsive after SetFrameRate? {'YES' if alive else 'NO'}")
        if alive:
            print("  -> 0xFF-wedge hypothesis SUPPORTED. Iterate start seq without 0xFF.")
        else:
            print("  -> still wedged even without 0xFF; wedge is not the trailing byte.")
    finally:
        log_trial("start_8hz", log, meta={"phase": "wedge-test-8hz"})
        h.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
stream_test.py — the clean two-command start sequence, then listen.

listen.py proved SetFrameRate (0x39) only ACKs; it does NOT auto-stream. The ELF
manual's flow is two distinct actions: Record>Settings (set rate) then
Record>Start. At the wire level that is SetFrameRate (0x39) then StartRecording
(0x3d). The earlier handshake polluted the front with GetFWversion; this tests
the MINIMAL clean sequence with nothing before it.

Run right after a FRESH REPLUG.
  init -> SetFrameRate(39 50 15 ff) -> read ack -> StartRecording(0x3d) -> listen 12s
Every byte burst is timestamped. A sustained burst after 0x3d = WE HAVE A STREAM.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402

SETRATE = bytes([0x39, 0x50, 0x15, 0xff])   # SetFrameRate @100Hz (decoded)
START = bytes([0x3d])                        # StartRecording (argc 0)


def read_for(f, secs, t0, bursts, tag):
    end = time.time() + secs
    while time.time() < end:
        d = f.read_data_bytes(256, attempt=2)
        if d:
            t = time.time() - t0
            bursts.append((tag, round(t, 3), bytes(d).hex()))
            print(f"  [{tag:9}] t={t:6.3f}s +{len(d):3}B  {bytes(d).hex()}")


def parse_frames(hexstr):
    raw = bytes.fromhex(hexstr)
    vals, i = [], 0
    while i + 1 < len(raw):
        if (raw[i] ^ raw[i + 1]) == 0xFF:
            vals.append(raw[i]); i += 2
        else:
            i += 1
    return vals


def main():
    print("Clean start sequence: SetFrameRate -> StartRecording -> listen")
    print("=" * 62)
    h = TekscanHandle()
    f = h.ftdi
    bursts = []
    try:
        f.purge_buffers(); time.sleep(0.003)
        t0 = time.time()
        f.write_data(SETRATE)
        print(f"  sent SetFrameRate {SETRATE.hex()} at t=0")
        read_for(f, 0.6, t0, bursts, "setrate")
        f.write_data(START)
        print(f"  sent StartRecording {START.hex()} at t={time.time()-t0:.3f}")
        read_for(f, 12.0, t0, bursts, "afterstart")
        # summary
        after = [b for b in bursts if b[0] == "afterstart"]
        nbytes = sum(len(bytes.fromhex(b[2])) for b in after)
        allhex = "".join(b[2] for b in after)
        frames = parse_frames(allhex)
        print(f"\n  after StartRecording: {len(after)} bursts, {nbytes} bytes, "
              f"{len(frames)} [v,~v] frames")
        if frames:
            print(f"  values: min={min(frames)} max={max(frames)} sample={frames[:20]}")
            print("  *** STREAM! Press the pad / add weight and watch values change. ***")
        elif nbytes > 6:
            print("  bytes flowing but not [v,~v] frames — note the framing; we're close.")
        else:
            print("  no stream after StartRecording either. Next: try the connect/")
            print("  select-channel sequence (live data may need it, per OnConnect).")
    finally:
        log_trial("stream_test", {"setrate": SETRATE.hex(), "start": START.hex(),
                  "bursts": bursts}, meta={"phase": "clean-start-seq"})
        h.close()


if __name__ == "__main__":
    main()

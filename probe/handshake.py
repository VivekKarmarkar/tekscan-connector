#!/usr/bin/env python3
"""
handshake.py — single-shot full-sequence diagnostic for the ELF handle.

WHY: scan_attempt.py showed the device replies `c0 80 c0` to the decoded
SetFrameRate command `39 50 15 ff`, then goes silent (one response per physical
power-up; the CBUS reset is not a true power cycle). So we must do the WHOLE
handshake inside ONE power-up, in one open session, and print every raw byte.

This sends a candidate command SEQUENCE and dumps all bytes after each step so we
can see: what SetFrameRate really returns, whether a follow-up command gets
through in the same session, and whether StartRecording (0x3d) triggers a stream.

RUN IMMEDIATELY AFTER A FRESH PHYSICAL REPLUG (the device's one-shot is spent
otherwise). One open, no re-init between steps.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from triallog import log_trial  # noqa: E402
from tekscan_connector.protocol import TekscanHandle  # noqa: E402


def read_for(ftdi, secs):
    buf, t0 = bytearray(), time.time()
    while time.time() - t0 < secs:
        d = ftdi.read_data_bytes(256, attempt=2)
        if d:
            buf += d
    return bytes(buf)


def step(ftdi, name, packet, read_secs, purge=False):
    if purge:
        ftdi.purge_buffers(); time.sleep(0.002)
    ftdi.write_data(packet)
    raw = read_for(ftdi, read_secs)
    print(f"  {name:26} sent {packet.hex():10} -> {len(raw):4}B  {raw.hex()}")
    return raw


def main():
    print("ELF full-handshake diagnostic (run right after a fresh replug)")
    print("=" * 64)
    h = TekscanHandle()                      # one open, CBUS reset, UART
    f = h.ftdi
    log = {}
    try:
        # Step 0: is the device alive on a known-good query? GetFWversion = 0x44.
        log["getfw"] = step(f, "GetFWversion(0x44)", bytes([0x44]), 0.3, purge=True).hex()
        # Step 1: SetFrameRate @100Hz (the decoded command). Capture its ACK.
        log["setrate"] = step(f, "SetFrameRate 39 50 15 ff", bytes([0x39, 0x50, 0x15, 0xff]), 0.8).hex()
        # Step 2: StartRecording (0x3d) — maybe THIS begins the stream after rate is set.
        log["startrec"] = step(f, "StartRecording(0x3d)", bytes([0x3d]), 2.0).hex()
        # Step 3: if still no stream, is the device still answering? re-query FW.
        log["getfw2"] = step(f, "GetFWversion(0x44) again", bytes([0x44]), 0.3, purge=True).hex()
        # Step 4: CollectSingle (0x30) — single-frame poll, see if one value comes.
        log["collect"] = step(f, "CollectSingle(0x30)", bytes([0x30]), 0.3, purge=True).hex()
    finally:
        log_trial("handshake_diag", log, meta={"phase": "handshake", "note": "fresh-replug single session"})
        h.close()
    print("\nLogged to probe/results/. Key question: did StartRecording (step 2) produce a burst?")


if __name__ == "__main__":
    main()

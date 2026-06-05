#!/usr/bin/env python3
"""
probe_handle.py — capture + analyze the Tekscan ELF handle's raw USB byte stream.

WHY THIS EXISTS
---------------
The handle is an FTDI device (USB 0x11DA:0x0012, "Tekscan USB ELF handle"),
driven by Tekscan over D2XX (FT245-style FIFO; virtual COM port disabled). The
transport is fully solved; the application byte protocol is NOT publicly known
(nobody has reverse-engineered it — every existing Tekscan tool uses the Windows
.NET SDK). This tool is the reverse-engineering instrument.

It opens the handle directly with pyftdi (the D2XX-equivalent — FT245 ASYNC FIFO
needs no MPSSE/bitmode, just read_data_bytes), records the raw stream to a .bin,
and prints structure-revealing stats (byte histogram, candidate frame length).
A GUIDED mode prompts you to place / remove the 1000 g weight at timed marks so
the bytes that move with load become obvious.

Known payload semantics (from the ELF manual): each sensor → one 8-bit value
(0-255) per frame, 8-200 Hz. So we expect small periodic frames of 0-255 counts.

TRANSPORTS (pick one):
  • pyftdi (default)         — libusb, matches Windows D2XX. Auto-detaches kernel.
  • --tty /dev/ttyUSB0       — if you bound it via:  sudo modprobe ftdi_sio &&
                               echo 11da 0012 | sudo tee \\
                               /sys/bus/usb-serial/drivers/ftdi_sio/new_id

USAGE
-----
  .venv/bin/python probe/probe_handle.py --list           # what's visible
  sudo .venv/bin/python probe/probe_handle.py --seconds 20
  sudo .venv/bin/python probe/probe_handle.py --guided    # follow PLACE/REMOVE
  .venv/bin/python probe/probe_handle.py --tty /dev/ttyUSB0 --guided

sudo is unnecessary if you install udev/99-tekscan.rules. Read-only by default;
--send-hex writes a candidate wake-up command once before capturing.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Callable

TEK_VID = 0x11DA
ELF_PID = 0x0012
CAPTURE_DIR = Path(__file__).resolve().parent.parent / "captures"

ReadFn = Callable[[], bytes]


# --------------------------------------------------------------------------- #
# pyftdi transport (primary)
# --------------------------------------------------------------------------- #
def _import_pyftdi():
    try:
        from pyftdi.ftdi import Ftdi
        return Ftdi
    except ImportError:
        sys.exit("pyftdi not installed. Run: .venv/bin/pip install -r requirements.txt")


def _register_ids(Ftdi) -> None:
    """Teach pyftdi about Tekscan's non-standard VID/PID so open()/list() work."""
    try:
        Ftdi.add_custom_vendor(TEK_VID, "tekscan")
        Ftdi.add_custom_product(TEK_VID, ELF_PID, "elf_handle")
    except ValueError:
        pass  # already registered in this interpreter


def list_devices(Ftdi) -> int:
    _register_ids(Ftdi)
    print("Scanning for FTDI devices (incl. Tekscan 0x11DA)...")
    try:
        devices = Ftdi.list_devices()
    except Exception as exc:  # noqa: BLE001 — surface libusb/permission errors
        print(f"  ! could not enumerate: {exc}")
        _permission_hint(exc)
        return 1
    if not devices:
        print("  (none found)")
        print("  -> Is the HANDLE (blue-button piece) plugged in? It is a separate")
        print("     device from the software USB stick.")
        return 1
    for desc, ifcount in devices:
        tek = " <-- TEKSCAN ELF HANDLE" if (desc.vid, desc.pid) == (TEK_VID, ELF_PID) else ""
        print(f"  {desc.vid:#06x}:{desc.pid:#06x}  bus={desc.bus} addr={desc.address} "
              f"ifaces={ifcount} sn={desc.sn!r} desc={desc.description!r}{tek}")
    return 0


def open_ftdi(Ftdi):
    _register_ids(Ftdi)
    ftdi = Ftdi()
    ftdi.open(vendor=TEK_VID, product=ELF_PID, interface=1)
    # Report the actual silicon — tells us FT245R vs FT2232 etc. (async vs sync FIFO).
    try:
        print(f"  FTDI chip: {ftdi.ic_name}  (device_version={ftdi.device_version:#06x})")
    except Exception:  # noqa: BLE001
        pass
    # Normal byte-FIFO mode; 1 ms latency so small frames return promptly.
    for setter in (lambda: ftdi.set_bitmode(0x00, Ftdi.BitMode.RESET),
                   lambda: ftdi.set_latency_timer(1)):
        try:
            setter()
        except Exception:  # noqa: BLE001 — non-fatal on parts that reject it
            pass
    return ftdi


# --------------------------------------------------------------------------- #
# pyserial transport (fallback: kernel ftdi_sio + new_id -> /dev/ttyUSB0)
# --------------------------------------------------------------------------- #
def open_tty(path: str, baud: int):
    try:
        import serial
    except ImportError:
        sys.exit("pyserial not installed. Run: .venv/bin/pip install -r requirements.txt")
    print(f"  opening serial {path} @ {baud} (baud is a near-no-op for a FIFO part)")
    return serial.Serial(path, baud, timeout=0.05)


# --------------------------------------------------------------------------- #
# capture + analysis (transport-agnostic)
# --------------------------------------------------------------------------- #
def capture(read: ReadFn, seconds: float, guided: bool, out_path: Path) -> bytes:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    chunks: list[bytes] = []
    marks: list[tuple[float, int, str]] = []
    total = 0
    t0 = time.monotonic()

    def mark(label: str) -> None:
        marks.append((time.monotonic() - t0, total, label))
        print(f"  [t+{time.monotonic() - t0:5.1f}s  @byte {total:7d}]  {label}")

    print(f"\nCapturing for {seconds:.0f}s -> {out_path}")
    if guided:
        print("Follow the prompts. Keep a sensor inserted; sensor pad accessible.")
    script = _guided_script(seconds) if guided else []
    si = 0
    while (elapsed := time.monotonic() - t0) < seconds:
        while si < len(script) and elapsed >= script[si][0]:
            mark(script[si][1])
            si += 1
        data = read()
        if data:
            chunks.append(bytes(data))
            total += len(data)
        else:
            time.sleep(0.005)

    buf = b"".join(chunks)
    out_path.write_bytes(buf)
    if marks:
        side = out_path.with_suffix(".marks.txt")
        side.write_text("\n".join(f"{t:.3f}\t{off}\t{lbl}" for t, off, lbl in marks))
        print(f"  wrote load marks -> {side}")
    print(f"  wrote {len(buf)} bytes -> {out_path}")
    return buf


def _guided_script(seconds: float) -> list[tuple[float, str]]:
    return [
        (1.0, "NO LOAD — leave the sensor empty"),
        (max(4.0, seconds * 0.25), "PLACE the 1000 g weight on the sensor"),
        (max(8.0, seconds * 0.50), "REMOVE the weight"),
        (max(12.0, seconds * 0.70), "PLACE the weight again"),
        (max(16.0, seconds * 0.90), "REMOVE the weight (final)"),
    ]


def analyze(buf: bytes) -> None:
    print(f"\n=== capture analysis ({len(buf)} bytes) ===")
    if not buf:
        print("  NO bytes were read -> the handle does not stream unsolicited; it")
        print("  likely needs an init/start command. Next: capture the Windows")
        print("  ELF<->handle exchange (Wine/VM + usbmon) or try --send-hex guesses.")
        return
    hist = Counter(buf)
    print(f"  distinct byte values: {len(hist)}/256")
    print("  most common: " + ", ".join(f"{b:#04x}x{n}" for b, n in hist.most_common(6)))
    # Cheap periodicity scan: the lag p (2..64) that best satisfies buf[i]==buf[i+p]
    # spikes at the frame length for a clean periodic stream.
    n = len(buf)
    best_p, best = None, 0.0
    for p in range(2, min(64, n // 4) + 1):
        score = sum(buf[i] == buf[i + p] for i in range(n - p)) / (n - p)
        if score > best:
            best_p, best = p, score
    if best_p:
        print(f"  best repeating period: {best_p} bytes (self-match {best:.0%}) "
              f"-> candidate frame length")
    print(f"  first 64 bytes: {buf[:64].hex(' ')}")


def _permission_hint(exc: Exception) -> None:
    msg = str(exc).lower()
    if any(k in msg for k in ("access", "permission", "errno 13", "busy")):
        print("  -> permissions/contention. Either run with sudo, or install the rule:")
        print("     sudo cp udev/99-tekscan.rules /etc/udev/rules.d/ &&")
        print("     sudo udevadm control --reload-rules && sudo udevadm trigger")


# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Probe the Tekscan ELF handle byte stream.")
    ap.add_argument("--list", action="store_true", help="list visible FTDI devices and exit")
    ap.add_argument("--seconds", type=float, default=20.0, help="capture duration")
    ap.add_argument("--guided", action="store_true", help="prompt for weight place/remove")
    ap.add_argument("--out", type=Path, default=None, help="output .bin path")
    ap.add_argument("--tty", default=None,
                    help="read from this serial device instead of pyftdi (e.g. /dev/ttyUSB0)")
    ap.add_argument("--baud", type=int, default=921600, help="baud for --tty (FIFO: ~no-op)")
    ap.add_argument("--send-hex", default=None,
                    help="OPTIONAL: hex bytes to write once before capture (e.g. '1b 53')")
    args = ap.parse_args(argv)

    # --- open chosen transport, build a read() closure --------------------- #
    closer: Callable[[], None] = lambda: None
    if args.tty:
        ser = open_tty(args.tty, args.baud)
        if args.send_hex:
            payload = bytes.fromhex(args.send_hex.replace(",", " "))
            print(f"Writing {len(payload)} byte(s): {payload.hex(' ')}")
            ser.write(payload)
            time.sleep(0.05)
        read: ReadFn = lambda: ser.read(4096)
        closer = ser.close
    else:
        Ftdi = _import_pyftdi()
        if args.list:
            return list_devices(Ftdi)
        try:
            ftdi = open_ftdi(Ftdi)
        except Exception as exc:  # noqa: BLE001
            print(f"Could not open the handle (0x{TEK_VID:04x}:0x{ELF_PID:04x}): {exc}")
            _permission_hint(exc)
            print("Tip: run `--list` first to confirm the handle is present.")
            return 1
        if args.send_hex:
            payload = bytes.fromhex(args.send_hex.replace(",", " "))
            print(f"Writing {len(payload)} byte(s): {payload.hex(' ')}")
            ftdi.write_data(payload)
            time.sleep(0.05)
        read = lambda: bytes(ftdi.read_data_bytes(4096, attempt=2))
        closer = ftdi.close

    # --- capture ----------------------------------------------------------- #
    try:
        out = args.out or (CAPTURE_DIR / f"capture-{int(time.time())}.bin")
        buf = capture(read, args.seconds, args.guided, out)
        analyze(buf)
    finally:
        closer()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

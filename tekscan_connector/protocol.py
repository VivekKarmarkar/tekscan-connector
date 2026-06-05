#!/usr/bin/env python3
"""
protocol.py — the Tekscan ELF handle wire protocol, recovered from ElfMPort.exe
via Ghidra decompilation (FUN_00446f30 = connect, FUN_00409d50 =
ButtCellDevice::OnNewDataAvailable) and confirmed against the live device.

INIT (exact, from the connect method):
  FT_OpenEx(serial) → SetBitMode(0x80,CBUS) [CBUS3 low=reset] → StopInTask →
  SetBaudRate(750000) → 8N1 → FlowControl(none) → LatencyTimer(16) →
  Timeouts(300,250) → Sleep(15) → Purge → SetEventNotification(RXCHAR) →
  RestartInTask → SetBitMode(0x88,CBUS) [CBUS3 high=run].
  (For libusb/pyftdi we additionally drop to UART mode to read — D2XX reads in
   CBUS mode but libusb does not.)

WIRE: send one register/channel byte → device replies [value][~value]
  (2 bytes; value is the 8-bit force count; byte1 == ~value validates the frame).
  0xFF (255) at no load = idle rail per the calibration code.
"""
import time
from pyftdi.ftdi import Ftdi

TEK_VID, ELF_PID = 0x11DA, 0x0012
BAUD = 750000
Ftdi.add_custom_vendor(TEK_VID, "tekscan")
Ftdi.add_custom_product(TEK_VID, ELF_PID, "elf")


class TekscanHandle:
    """Linux-native driver for the Tekscan ELF handle (FT232R, no Windows/SDK)."""

    def __init__(self):
        self.ftdi = Ftdi()
        self.ftdi.open(vendor=TEK_VID, product=ELF_PID)
        self._init()

    def _init(self):
        # CBUS3 reset pulse (low->high) then drop to UART so libusb can read.
        # (D2XX leaves CBUS mode on; libusb needs UART mode to receive — the MCU
        #  is already released by the high pulse, so this is equivalent.)
        f = self.ftdi
        f.set_bitmode(0x80, Ftdi.BitMode.CBUS)      # CBUS3 low  (MCU reset asserted)
        f.set_baudrate(BAUD)
        f.set_line_property(8, 1, 'N')              # 8N1
        f.set_latency_timer(2)
        time.sleep(0.02)
        f.set_bitmode(0x88, Ftdi.BitMode.CBUS)      # CBUS3 high (MCU released)
        time.sleep(0.02)
        f.set_bitmode(0x00, Ftdi.BitMode.RESET)     # UART mode (libusb read path)
        f.purge_buffers()
        time.sleep(0.04)

    def _read(self, secs):
        buf = bytearray(); t0 = time.time()
        while time.time() - t0 < secs:
            d = self.ftdi.read_data_bytes(64, attempt=3)
            if d: buf += d
        return bytes(buf)

    def read_register(self, reg, timeout=0.03):
        """Send a register/channel byte; return its 8-bit value, or None if no
        valid [value][~value] frame came back."""
        self.ftdi.purge_buffers()
        time.sleep(0.002)
        self.ftdi.write_data(bytes([reg]))
        r = self._read(timeout)
        if len(r) == 2 and (r[0] ^ r[1]) == 0xFF:   # checksum: byte1 == ~byte0
            return r[0]
        return None

    def close(self):
        try: self.ftdi.close()
        except Exception: pass


if __name__ == "__main__":
    # Verify the decoded protocol reads candidate registers cleanly (no load).
    h = TekscanHandle()
    print("reading candidate registers with checksum validation:")
    for reg in (0x44, 0x61, 0x70, 0x30, 0x3e, 0x62, 0x05):
        vals = [h.read_register(reg) for _ in range(5)]
        print(f"  reg {reg:#04x}: {vals}")
    h.close()

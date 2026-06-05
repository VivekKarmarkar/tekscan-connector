"""
tekscan_connector — a lean, Linux-native bridge from a Tekscan FlexiForce ELF
handle to Python (and, ultimately, an MCP server for Claude Code).

The ELF handle is an FTDI device: USB 0x11DA:0x0012 ("Tekscan USB ELF handle"),
driven over FTDI D2XX (FT245-style FIFO; the Windows virtual COM port is disabled).

Modules (Unix-philosophy: each does one thing):
  ftdi_link    — transport: open the handle by VID/PID, read/write raw bytes
  protocol     — frame decode (TODO: filled in once the byte protocol is captured)
  calibration  — raw counts -> force, via a known reference weight (your 1000 g)
  reader       — high-level glue: link + protocol + calibration -> force readings

Status: the FTDI transport + calibration are known; the application byte
protocol is the one remaining unknown (see probe/probe_handle.py).
"""

TEKSCAN_VID = 0x11DA
ELF_HANDLE_PID = 0x0012
# Sibling Tekscan FTDI devices, from the Tek_Evo.inf driver file:
KNOWN_TEKSCAN_PIDS = {
    0x0012: "Tekscan USB ELF handle",
    0x0020: "Tekscan Evolution",
    0x0028: "Tekscan Seat Sensor",
    0x0018: "Genesis (channel A/B)",
}

__all__ = ["TEKSCAN_VID", "ELF_HANDLE_PID", "KNOWN_TEKSCAN_PIDS"]

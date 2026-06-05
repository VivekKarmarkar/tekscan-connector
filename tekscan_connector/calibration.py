"""
calibration.py — map the handle's raw counts to real force.

The ELF handle's electronics emit an 8-bit value (0-255 "Raw") proportional to
the sensor's conductance under load. A FlexiForce sensor is, to first order,
linear once conditioned (Tekscan quotes linearity within ~+-3%). So a two-point
calibration — one reading at zero load, one at a known reference weight — is
enough to convert raw counts to force.

This module is deliberately independent of the (still-unknown) byte protocol:
it works on whatever scalar "raw" value the decoder eventually hands us.

Units: the user calibrates with a known MASS (e.g. 1000 g). We convert mass to
force with standard gravity and expose both newtons and gram-force.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path

STANDARD_GRAVITY = 9.80665  # m/s^2 (CODATA / ISO 80000-3)


@dataclass
class Calibration:
    """A two-point (zero + one reference weight) linear calibration.

    force(raw) is the line through (raw_zero, 0) and (raw_ref, ref_force).
    """

    raw_zero: float        # mean raw counts at NO load
    raw_ref: float         # mean raw counts at the reference load
    ref_grams: float       # the known calibration mass, in grams (e.g. 1000.0)
    sensitivity: int | None = None   # ELF "sensitivity" gain setting, if known
    note: str = ""
    created: float = 0.0   # epoch seconds; stamped by two_point()

    # --- derived quantities -------------------------------------------------
    @property
    def ref_newtons(self) -> float:
        return (self.ref_grams / 1000.0) * STANDARD_GRAVITY

    @property
    def span(self) -> float:
        return self.raw_ref - self.raw_zero

    def _check(self) -> None:
        if self.span == 0:
            raise ValueError(
                "degenerate calibration: raw_ref == raw_zero "
                "(the weight produced no change in counts — check loading/sensitivity)"
            )

    # --- conversions --------------------------------------------------------
    def raw_to_newtons(self, raw: float) -> float:
        self._check()
        return (raw - self.raw_zero) / self.span * self.ref_newtons

    def raw_to_grams_force(self, raw: float) -> float:
        """Force expressed as gram-force (gf): what mass would exert this force."""
        return self.raw_to_newtons(raw) / STANDARD_GRAVITY * 1000.0

    # --- persistence --------------------------------------------------------
    DEFAULT_PATH = Path.home() / ".config" / "tekscan-connector" / "calibration.json"

    def save(self, path: str | Path | None = None) -> Path:
        p = Path(path) if path else self.DEFAULT_PATH
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2))
        return p

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Calibration":
        p = Path(path) if path else cls.DEFAULT_PATH
        return cls(**json.loads(p.read_text()))

    @classmethod
    def exists(cls, path: str | Path | None = None) -> bool:
        p = Path(path) if path else cls.DEFAULT_PATH
        return p.is_file()

    # --- construction -------------------------------------------------------
    @classmethod
    def two_point(
        cls,
        raw_zero: float,
        raw_ref: float,
        ref_grams: float,
        *,
        sensitivity: int | None = None,
        note: str = "",
    ) -> "Calibration":
        cal = cls(
            raw_zero=raw_zero,
            raw_ref=raw_ref,
            ref_grams=ref_grams,
            sensitivity=sensitivity,
            note=note,
            created=time.time(),
        )
        cal._check()
        return cal


if __name__ == "__main__":
    # Self-check: a fabricated calibration where 1000 g moves the counts 0 -> 200.
    cal = Calibration.two_point(raw_zero=5.0, raw_ref=205.0, ref_grams=1000.0,
                                note="self-check (fabricated)")
    assert abs(cal.raw_to_grams_force(205.0) - 1000.0) < 1e-6
    assert abs(cal.raw_to_grams_force(5.0) - 0.0) < 1e-6
    # Halfway up the counts -> roughly half the reference mass.
    assert abs(cal.raw_to_grams_force(105.0) - 500.0) < 1e-6
    print("calibration self-check OK")
    print(f"  ref: {cal.ref_grams:.0f} g  = {cal.ref_newtons:.4f} N")
    print(f"  raw 105 -> {cal.raw_to_newtons(105.0):.4f} N "
          f"({cal.raw_to_grams_force(105.0):.1f} gf)")

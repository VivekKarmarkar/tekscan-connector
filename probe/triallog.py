"""Append-only trial logger for Tekscan FlexiForce ELF probe runs.

Purpose
-------
Earlier live trials printed their raw numeric output to the terminal and were
lost when the conversation rolled over. From now on, every live trial captures
its output to a timestamped JSON file in ``probe/results/`` so nothing is ever
narrated-and-forgotten again.

Design
------
This is a NEW, standalone helper. It deliberately does not modify any of the
existing (working) probe scripts. New probe scripts opt in with::

    from triallog import log_trial
    log_trial("scan_attempt", {"reg": 0x20, "frames": [...]}, meta={"weight_g": 500})

One module, one job: persist a trial record. Unix philosophy.
"""

from __future__ import annotations

import datetime
import json
import os
import platform
import time

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def _utc_stamp() -> str:
    """UTC timestamp safe for filenames, e.g. 20260604T013500Z."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def log_trial(label: str, data, meta: dict | None = None) -> str:
    """Persist one trial record to ``probe/results/<utc>__<label>.json``.

    Parameters
    ----------
    label : str
        Short kebab/snake identifier for the trial (becomes part of the filename).
    data : Any JSON-serializable
        The raw trial payload (register readings, frame bytes, sweep results...).
    meta : dict, optional
        Context that makes the trial interpretable later: applied weight, whether
        the sensor was inserted, which command was sent, device serial, etc.

    Returns
    -------
    str
        The absolute path of the written file.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = _utc_stamp()
    record = {
        "label": label,
        "utc": ts,
        "epoch": time.time(),
        "host": platform.node(),
        "meta": meta or {},
        "data": data,
    }
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
    path = os.path.join(RESULTS_DIR, f"{ts}__{safe_label}.json")
    with open(path, "w") as fh:
        json.dump(record, fh, indent=2, default=repr)
    print(f"[triallog] wrote {path}")
    return path


if __name__ == "__main__":
    # Smoke test: writing a record proves the results dir + serialization work.
    p = log_trial("triallog_selftest", {"hello": "world", "bytes": [255, 0]},
                  meta={"note": "self-test, safe to delete"})
    print("self-test OK ->", p)

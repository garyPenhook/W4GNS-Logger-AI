"""Minimal ADIF import/export helpers.

We support the most common fields used by this logger. The parser is intentionally
simple and tolerant; it looks for <TAG:len>value pairs and splits on <EOR>.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List

from .models import QSO

# Minimal ADIF parser/writer for common fields used by the logger.
# ADIF spec: https://www.adif.org/


FIELD_MAP_IN = {
    "CALL": "call",
    "QSO_DATE": "date",
    "TIME_ON": "time",
    "BAND": "band",
    "MODE": "mode",
    "FREQ": "freq_mhz",
    "RST_SENT": "rst_sent",
    "RST_RCVD": "rst_rcvd",
    "NAME": "name",
    "QTH": "qth",
    "GRIDSQUARE": "grid",
    "COUNTRY": "country",
    "COMMENT": "comment",
}

FIELD_MAP_OUT = {
    "call": "CALL",
    "band": "BAND",
    "mode": "MODE",
    "freq_mhz": "FREQ",
    "rst_sent": "RST_SENT",
    "rst_rcvd": "RST_RCVD",
    "name": "NAME",
    "qth": "QTH",
    "grid": "GRIDSQUARE",
    "country": "COUNTRY",
    "comment": "COMMENT",
}


def _parse_adif_record(text: str) -> Dict[str, str]:
    """Extract a dict of ADIF tag->value from a single record chunk.

    This is a best-effort parser that respects <TAG:len>value and ignores type hints.
    """
    i = 0
    n = len(text)
    rec: Dict[str, str] = {}
    while i < n:
        if text[i] != "<":
            i += 1
            continue
        j = text.find(">", i)
        if j == -1:
            break
        tag = text[i + 1 : j]
        parts = tag.split(":")
        name = parts[0].upper()
        length = None
        if len(parts) >= 2:
            try:
                length = int(parts[1])
            except ValueError:
                length = None
        # Skip type (parts[2]) if present
        i = j + 1
        if length is None:
            # No length; skip
            continue
        val = text[i : i + length]
        rec[name] = val
        i += length
    return rec


def load_adif(text: str) -> List[QSO]:
    """Parse ADIF text into a list of QSO objects (best effort).

    Records without CALL or without both QSO_DATE and TIME_ON are skipped.
    Invalid data is logged and skipped gracefully.
    """
    records: List[QSO] = []
    # Split by <EOR>
    for chunk in text.split("<EOR>"):
        try:
            rec = _parse_adif_record(chunk)
            if not rec:
                continue
            # Build QSO from fields
            call = rec.get("CALL")
            if not call:
                continue
            date = rec.get("QSO_DATE")
            time = rec.get("TIME_ON")
            dt = None
            if date and time:
                try:
                    # yyyymmdd + hhmm[ss]
                    if len(date) < 8 or len(time) < 4:
                        continue  # Skip invalid date/time format
                    y, m, d = int(date[0:4]), int(date[4:6]), int(date[6:8])
                    hh, mm = int(time[0:2]), int(time[2:4])
                    ss = int(time[4:6]) if len(time) >= 6 else 0
                    dt = datetime(y, m, d, hh, mm, ss)
                except (ValueError, IndexError) as e:
                    # Skip records with invalid date/time
                    continue
            else:
                # If missing, skip record
                continue

            # Parse frequency with error handling
            freq_mhz = None
            if rec.get("FREQ"):
                try:
                    freq_mhz = float(rec["FREQ"])
                except (ValueError, TypeError):
                    freq_mhz = None

            q = QSO(
                call=call,
                start_at=dt,
                band=rec.get("BAND"),
                mode=rec.get("MODE"),
                freq_mhz=freq_mhz,
                rst_sent=rec.get("RST_SENT"),
                rst_rcvd=rec.get("RST_RCVD"),
                name=rec.get("NAME"),
                qth=rec.get("QTH"),
                grid=rec.get("GRIDSQUARE"),
                country=rec.get("COUNTRY"),
                comment=rec.get("COMMENT"),
            )
            records.append(q)
        except Exception:
            # Skip any record that causes unexpected errors
            continue
    return records


def dump_adif(qsos: Iterable[QSO]) -> str:
    """Serialize QSOs to ADIF text with a minimal header and <EOR>-terminated records."""
    lines: List[str] = ["<ADIF_VER:3>3.1", "<PROGRAMID:13>W4GNS Logger", "<EOH>"]
    for q in qsos:
        dt = q.start_at
        date = dt.strftime("%Y%m%d")
        time = dt.strftime("%H%M%S")

        def field(tag: str, value: str) -> str:
            return f"<{tag}:{len(value)}>{value}"

        rec: List[str] = []
        rec.append(field("QSO_DATE", date))
        rec.append(field("TIME_ON", time))
        rec.append(field("CALL", q.call))
        if q.band:
            rec.append(field("BAND", q.band))
        if q.mode:
            rec.append(field("MODE", q.mode))
        if q.freq_mhz is not None:
            rec.append(field("FREQ", f"{q.freq_mhz:.6f}".rstrip("0").rstrip(".")))
        if q.rst_sent:
            rec.append(field("RST_SENT", q.rst_sent))
        if q.rst_rcvd:
            rec.append(field("RST_RCVD", q.rst_rcvd))
        if q.name:
            rec.append(field("NAME", q.name))
        if q.qth:
            rec.append(field("QTH", q.qth))
        if q.grid:
            rec.append(field("GRIDSQUARE", q.grid))
        if q.country:
            rec.append(field("COUNTRY", q.country))
        if q.comment:
            rec.append(field("COMMENT", q.comment))
        rec.append("<EOR>")
        lines.append("".join(rec))
    return "\n".join(lines) + ("\n" if lines else "")

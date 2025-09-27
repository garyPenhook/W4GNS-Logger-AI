"""Data models used by W4GNS Logger AI.

Currently we expose a single SQLModel table, QSO, which represents an
individual contact. Fields are deliberately practical (band, mode, grid, etc.).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class QSO(SQLModel, table=True):
    """A single QSO (contact) entry stored in SQLite via SQLModel.

    Attributes
    - id: Surrogate primary key (autoincrement).
    - call: Worked station's callsign, uppercased when logged.
    - start_at: UTC timestamp of when the QSO started (naive UTC).
    - band/mode/freq_mhz: Radio details; band and mode are free text like "20m" or "FT8".
    - rst_sent/rst_rcvd: Signal reports.
    - name/qth/grid/country: Operator/location metadata (optional).
    - comment: Free-form notes.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    call: str = Field(index=True, description="Station callsign")
    start_at: datetime = Field(index=True, description="QSO start time (UTC)")

    # Radio details
    band: Optional[str] = Field(default=None, index=True)
    mode: Optional[str] = Field(default=None, index=True)
    freq_mhz: Optional[float] = Field(default=None, description="Frequency in MHz")

    # Reports
    rst_sent: Optional[str] = None
    rst_rcvd: Optional[str] = None

    # Operator/station info
    name: Optional[str] = None
    qth: Optional[str] = None
    grid: Optional[str] = Field(default=None, index=True)
    country: Optional[str] = None

    # Misc
    comment: Optional[str] = None


def now_utc() -> datetime:
    """Return the current time as a naive UTC datetime without microseconds.

    We intentionally store naive UTC to keep SQLite handling and output simple.
    """
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)

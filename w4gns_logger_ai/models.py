from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class QSO(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    call: str = Field(index=True, description="Station callsign")

    # Start time of QSO in UTC
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
    # produce naive UTC timestamp without microseconds
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)

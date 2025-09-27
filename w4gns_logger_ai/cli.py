"""Command-line interface for W4GNS Logger AI.

Commands cover initializing the database, logging QSOs, listing/searching,
ADIF import/export, AI summaries, and awards insights (deterministic + AI).
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

# Allow running this file directly by ensuring the project root is on sys.path
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import typer
from rich.console import Console
from rich.table import Table

from w4gns_logger_ai.adif import dump_adif, load_adif
from w4gns_logger_ai.ai_helper import evaluate_awards, summarize_qsos
from w4gns_logger_ai.awards import compute_summary, filtered_qsos, suggest_awards
from w4gns_logger_ai.models import QSO
from w4gns_logger_ai.storage import (
    APP_NAME,
    add_qso,
    create_db_and_tables,
    delete_qso,
    get_db_path,
    list_qsos,
    search_qsos,
)

app = typer.Typer(add_completion=False, help=f"{APP_NAME} - Ham radio QSO logger")
awards_app = typer.Typer(help="Awards-related insights (deterministic + AI)")
app.add_typer(awards_app, name="awards")
console = Console()


# Utilities

def _parse_when(when: Optional[str]) -> datetime:
    """Parse a human-friendly UTC time string.

    Accepts "now" (default) or formats like YYYY-MM-DD, YYYY-MM-DD HH:MM[:SS], or ISO.
    Returns a naive UTC datetime.

    Raises typer.BadParameter for invalid datetime formats.
    """
    try:
        if not when or when.lower() == "now":
            # produce naive UTC timestamp without microseconds
            return datetime.now(UTC).replace(tzinfo=None, microsecond=0)
        # Accept formats: YYYY-MM-DD, YYYY-MM-DD HH:MM, YYYY-MM-DD HH:MM:SS, ISO 8601
        s = when.replace("T", " ").replace("Z", "")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        # Fallback to fromisoformat if possible
        try:
            return datetime.fromisoformat(when)
        except (ValueError, TypeError) as e:
            raise typer.BadParameter(f"Unrecognized datetime format: {when}") from e
    except Exception as e:
        if isinstance(e, typer.BadParameter):
            raise
        raise typer.BadParameter(f"Error parsing datetime '{when}': {e}") from e


def _ensure_db() -> None:
    """Ensure the SQLite database and tables exist (idempotent).

    Raises typer.Exit on database creation failure.
    """
    try:
        create_db_and_tables()
    except Exception as e:
        console.print(f"[red]Error creating database: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def init() -> None:
    """Create the database in your user data directory (or W4GNS_DB_PATH)."""
    try:
        path = create_db_and_tables()
        console.print(f"Database ready at: [bold]{path}[/bold]")
    except Exception as e:
        console.print(f"[red]Error initializing database: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def log(
    call: str = typer.Option(..., help="Station callsign, e.g., K1ABC"),
    when: Optional[str] = typer.Option("now", help="UTC time: 'now' or 'YYYY-MM-DD HH:MM[:SS]'"),
    band: Optional[str] = typer.Option(None, help="Band, e.g., 20m"),
    mode: Optional[str] = typer.Option(None, help="Mode, e.g., SSB, FT8"),
    freq: Optional[float] = typer.Option(None, help="Frequency in MHz"),
    rst_sent: Optional[str] = typer.Option(None, help="Report sent"),
    rst_rcvd: Optional[str] = typer.Option(None, help="Report received"),
    name: Optional[str] = typer.Option(None, help="Operator name"),
    qth: Optional[str] = typer.Option(None, help="QTH / city"),
    grid: Optional[str] = typer.Option(None, help="Maidenhead grid"),
    country: Optional[str] = typer.Option(None, help="DXCC country"),
    comment: Optional[str] = typer.Option(None, help="Comment"),
) -> None:
    """Log a new QSO with optional radio and operator metadata."""
    try:
        _ensure_db()
        dt = _parse_when(when)
        qso = QSO(
            call=call.upper(),
            start_at=dt,
            band=band,
            mode=mode,
            freq_mhz=freq,
            rst_sent=rst_sent,
            rst_rcvd=rst_rcvd,
            name=name,
            qth=qth,
            grid=grid,
            country=country,
            comment=comment,
        )
        saved = add_qso(qso)
        console.print(f"Saved QSO id={saved.id} with {saved.call} at {saved.start_at}Z")
    except Exception as e:
        console.print(f"[red]Error logging QSO: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("list")
def list_cmd(
    limit: int = typer.Option(20, min=1, max=1000, help="Max QSOs to show"),
    call: Optional[str] = typer.Option(None, help="Filter by callsign contains"),
) -> None:
    """Display recent QSOs in a table, optionally filtering by callsign substring."""
    try:
        _ensure_db()
        rows = list_qsos(limit=limit, call=call)
        if not rows:
            console.print("No QSOs found.")
            return
        table = Table(title=f"Recent QSOs (DB: {get_db_path()})", show_lines=False)
        table.add_column("ID", justify="right")
        table.add_column("UTC")
        table.add_column("Call")
        table.add_column("Band")
        table.add_column("Mode")
        table.add_column("Grid")
        table.add_column("Comment")
        for q in rows:
            table.add_row(
                str(q.id or ""),
                q.start_at.strftime("%Y-%m-%d %H:%M:%S"),
                q.call,
                q.band or "",
                q.mode or "",
                q.grid or "",
                (q.comment or "")[:40],
            )
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error listing QSOs: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def remove(qso_id: int = typer.Argument(..., help="QSO ID to delete")) -> None:
    """Delete a QSO by database id."""
    try:
        _ensure_db()
        if delete_qso(qso_id):
            console.print(f"Deleted QSO id={qso_id}")
        else:
            console.print(f"QSO id={qso_id} not found")
    except Exception as e:
        console.print(f"[red]Error deleting QSO: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def export(
    output: Path = typer.Option(
        ...,
        exists=False,
        dir_okay=False,
        writable=True,
        help="ADIF file to write",
    ),
    limit: int = typer.Option(1000, min=1, help="How many recent QSOs to export"),
    call: Optional[str] = typer.Option(None, help="Filter by callsign contains"),
) -> None:
    """Write recent QSOs to an ADIF file on disk."""
    try:
        _ensure_db()
        qsos = list_qsos(limit=limit, call=call)
        txt = dump_adif(qsos)
        output.write_text(txt, encoding="utf-8")
        console.print(f"Exported {len(qsos)} QSOs to {output}")
    except Exception as e:
        console.print(f"[red]Error exporting ADIF: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def import_adif(
    src: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        help="ADIF file to import",
    ),
) -> None:
    """Import QSOs from an ADIF file; callsigns are normalized to uppercase."""
    try:
        _ensure_db()
        text = src.read_text(encoding="utf-8", errors="ignore")
        qsos = load_adif(text)
        # Normalize callsigns
        for q in qsos:
            q.call = q.call.upper()
        count_before = len(list_qsos(limit=99999))
        for q in qsos:
            add_qso(q)
        count_after = len(list_qsos(limit=99999))
        console.print(f"Imported {len(qsos)} QSOs. Total now: {count_after} (was {count_before}).")
    except Exception as e:
        console.print(f"[red]Error importing ADIF: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def search(
    call: Optional[str] = typer.Option(None, help="Substring filter for call"),
    band: Optional[str] = typer.Option(None, help="Exact band value"),
    mode: Optional[str] = typer.Option(None, help="Exact mode value"),
    grid: Optional[str] = typer.Option(None, help="Exact grid square"),
    limit: int = typer.Option(100, min=1, help="Max results"),
    json_out: bool = typer.Option(False, help="Output as JSON"),
) -> None:
    """Search QSOs by field and print results as a table or JSON array."""
    try:
        _ensure_db()
        rows = search_qsos(call=call, band=band, mode=mode, grid=grid, limit=limit)
        if json_out:
            def to_dict(q: QSO):
                return {
                    "id": q.id,
                    "call": q.call,
                    "start_at": q.start_at.isoformat(),
                    "band": q.band,
                    "mode": q.mode,
                    "freq_mhz": q.freq_mhz,
                    "rst_sent": q.rst_sent,
                    "rst_rcvd": q.rst_rcvd,
                    "name": q.name,
                    "qth": q.qth,
                    "grid": q.grid,
                    "country": q.country,
                    "comment": q.comment,
                }
            console.print_json(data=[to_dict(q) for q in rows])
            return
        # Otherwise, pretty table
        table = Table(title=f"Search results ({len(rows)})")
        table.add_column("ID", justify="right")
        table.add_column("UTC")
        table.add_column("Call")
        table.add_column("Band")
        table.add_column("Mode")
        table.add_column("Grid")
        for q in rows:
            table.add_row(
                str(q.id or ""),
                q.start_at.strftime("%Y-%m-%d %H:%M:%S"),
                q.call,
                q.band or "",
                q.mode or "",
                q.grid or "",
            )
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error searching QSOs: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def summarize(limit: int = typer.Option(50, min=1, help="How many recent QSOs to include")) -> None:
    """Produce a short summary of recent QSOs (AI-enabled when available)."""
    try:
        _ensure_db()
        rows = list_qsos(limit=limit)
        text = summarize_qsos(rows)
        console.print(text)
    except Exception as e:
        console.print(f"[red]Error summarizing QSOs: {e}[/red]")
        raise typer.Exit(1) from e


@awards_app.command("summary")
def awards_summary(
    band: Optional[str] = typer.Option(None, help="Filter QSOs by band before computing"),
    mode: Optional[str] = typer.Option(None, help="Filter QSOs by mode before computing"),
    json_out: bool = typer.Option(False, help="Output JSON"),
    limit: int = typer.Option(10000, min=1, help="How many recent QSOs to consider"),
) -> None:
    """Compute and display awards-related counts and per-band grid stats."""
    try:
        _ensure_db()
        qsos = list_qsos(limit=limit)
        qsos = filtered_qsos(qsos, band=band, mode=mode)
        summary = compute_summary(qsos)
        if json_out:
            console.print_json(data=summary)
            return
        # Pretty print
        table = Table(title="Awards summary")
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        table.add_row("Total QSOs", str(summary["total_qsos"]))
        table.add_row("Unique countries", str(summary["unique_countries"]))
        table.add_row("Unique grids", str(summary["unique_grids"]))
        table.add_row("Unique calls", str(summary["unique_calls"]))
        table.add_row("Unique bands", str(summary["unique_bands"]))
        table.add_row("Unique modes", str(summary["unique_modes"]))
        gpb = summary.get("grids_per_band", {}) or {}
        if gpb:
            for b, c in sorted(gpb.items()):
                table.add_row(f"Grids on {b or 'unknown'}", str(c))
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error computing awards summary: {e}[/red]")
        raise typer.Exit(1) from e


@awards_app.command("suggest")
def awards_suggest(
    band: Optional[str] = typer.Option(None, help="Filter QSOs by band before computing"),
    mode: Optional[str] = typer.Option(None, help="Filter QSOs by mode before computing"),
    limit: int = typer.Option(10000, min=1, help="How many recent QSOs to consider"),
) -> None:
    """Show simple award suggestions (e.g., DXCC close) based on thresholds."""
    try:
        _ensure_db()
        qsos = filtered_qsos(list_qsos(limit=limit), band=band, mode=mode)
        summary = compute_summary(qsos)
        suggestions = suggest_awards(summary)
        if not suggestions:
            console.print("No award suggestions yet — keep logging!")
            return
        for s in suggestions:
            console.print(f"- {s}")
    except Exception as e:
        console.print(f"[red]Error generating award suggestions: {e}[/red]")
        raise typer.Exit(1) from e


@awards_app.command("eval")
def awards_eval(
    goals: Optional[str] = typer.Option(None, help="Your awards goals to tailor guidance"),
    band: Optional[str] = typer.Option(None, help="Filter QSOs by band before evaluating"),
    mode: Optional[str] = typer.Option(None, help="Filter QSOs by mode before evaluating"),
    limit: int = typer.Option(10000, min=1, help="How many recent QSOs to consider"),
) -> None:
    """Use AI (when available) to produce a short, actionable awards plan."""
    try:
        _ensure_db()
        qsos = filtered_qsos(list_qsos(limit=limit), band=band, mode=mode)
        text = evaluate_awards(qsos, goals=goals)
        console.print(text)
    except Exception as e:
        console.print(f"[red]Error evaluating awards: {e}[/red]")
        raise typer.Exit(1) from e


def main() -> None:  # pragma: no cover - exercised via CLI
    app()


if __name__ == "__main__":  # pragma: no cover
    main()

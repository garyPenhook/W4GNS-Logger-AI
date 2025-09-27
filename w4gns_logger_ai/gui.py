"""Desktop GUI for W4GNS Logger AI using Tkinter.

Tabs:
- Log: capture a new QSO via form fields.
- Browse: filter, view, and delete QSOs in a table.
- Awards: show deterministic awards summary and evaluate an AI plan.
- Tools: import/export ADIF and run a quick AI/local summary.
"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional

# Allow running this file directly by ensuring the project root is on sys.path
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from w4gns_logger_ai.adif import dump_adif, load_adif
from w4gns_logger_ai.ai_helper import evaluate_awards, summarize_qsos
from w4gns_logger_ai.awards import compute_summary, filtered_qsos
from w4gns_logger_ai.models import QSO, now_utc
from w4gns_logger_ai.storage import (
    APP_NAME,
    add_qso,
    create_db_and_tables,
    delete_qso,
    get_db_path,
    list_qsos,
    search_qsos,
)


class LoggerGUI:
    """Main Tkinter application with tabbed panes for common tasks."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the GUI, database, and notebook layout."""
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x600")
        create_db_and_tables()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        self._build_log_tab()
        self._build_browse_tab()
        self._build_awards_tab()
        self._build_tools_tab()

    # Log tab
    def _build_log_tab(self) -> None:
        """Create the "Log" tab with QSO entry fields and a Save button."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Log")

        row = 0

        def add_field(label: str, width: int = 20) -> tk.Entry:
            nonlocal row
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
            e = ttk.Entry(frame, width=width)
            e.grid(row=row, column=1, sticky="w", padx=6, pady=4)
            row += 1
            return e

        self.e_call = add_field("Call")
        self.e_band = add_field("Band (e.g., 20m)")
        self.e_mode = add_field("Mode (e.g., SSB, FT8)")
        self.e_freq = add_field("Freq MHz (e.g., 14.074)")
        self.e_rst_s = add_field("RST sent")
        self.e_rst_r = add_field("RST rcvd")
        self.e_name = add_field("Name")
        self.e_qth = add_field("QTH")
        self.e_grid = add_field("Grid")
        self.e_country = add_field("Country")

        ttk.Label(frame, text="Comment").grid(row=row, column=0, sticky="nw", padx=6, pady=4)
        self.t_comment = tk.Text(frame, width=40, height=4)
        self.t_comment.grid(row=row, column=1, sticky="w", padx=6, pady=4)
        row += 1

        btn = ttk.Button(frame, text="Save QSO", command=self._save_qso)
        btn.grid(row=row, column=1, sticky="w", padx=6, pady=8)

    def _save_qso(self) -> None:
        """Validate and persist the QSO entered into the Log tab."""
        call = (self.e_call.get() or "").strip().upper()
        if not call:
            messagebox.showwarning("Missing", "Callsign is required")
            return

        def parse_float(s: str) -> Optional[float]:
            try:
                return float(s)
            except (ValueError, TypeError):
                return None

        q = QSO(
            call=call,
            start_at=now_utc(),
            band=(self.e_band.get() or None) or None,
            mode=(self.e_mode.get() or None) or None,
            freq_mhz=parse_float(self.e_freq.get() or ""),
            rst_sent=(self.e_rst_s.get() or None) or None,
            rst_rcvd=(self.e_rst_r.get() or None) or None,
            name=(self.e_name.get() or None) or None,
            qth=(self.e_qth.get() or None) or None,
            grid=(self.e_grid.get() or None) or None,
            country=(self.e_country.get() or None) or None,
            comment=(self.t_comment.get("1.0", tk.END).strip() or None),
        )
        add_qso(q)
        messagebox.showinfo("Saved", f"Saved QSO with {q.call}")
        self._refresh_table()

    # Browse tab
    def _build_browse_tab(self) -> None:
        """Create the "Browse" tab with filters and a results table."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Browse")

        filters = ttk.Frame(frame)
        filters.pack(fill="x", padx=8, pady=6)

        ttk.Label(filters, text="Call contains:").pack(side="left")
        self.f_call = ttk.Entry(filters, width=16)
        self.f_call.pack(side="left", padx=6)

        ttk.Label(filters, text="Band:").pack(side="left")
        self.f_band = ttk.Entry(filters, width=10)
        self.f_band.pack(side="left", padx=6)

        ttk.Label(filters, text="Mode:").pack(side="left")
        self.f_mode = ttk.Entry(filters, width=10)
        self.f_mode.pack(side="left", padx=6)

        ttk.Button(filters, text="Refresh", command=self._refresh_table).pack(side="left", padx=6)
        ttk.Button(filters, text="Delete selected", command=self._delete_selected).pack(side="left", padx=6)

        self.tree = ttk.Treeview(
            frame,
            columns=("id", "utc", "call", "band", "mode", "grid", "comment"),
            show="headings",
        )
        for i, col in enumerate(["ID", "UTC", "Call", "Band", "Mode", "Grid", "Comment"]):
            self.tree.heading(self.tree["columns"][i], text=col)
            self.tree.column(
                self.tree["columns"][i], width=110 if col != "Comment" else 260
            )
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)

        self._refresh_table()

    def _refresh_table(self) -> None:
        """Populate the Browse table using current filters (call/band/mode)."""
        call = (self.f_call.get() or None) if hasattr(self, 'f_call') else None
        band = (self.f_band.get() or None) if hasattr(self, 'f_band') else None
        mode = (self.f_mode.get() or None) if hasattr(self, 'f_mode') else None
        rows = search_qsos(call=call, band=band, mode=mode, limit=1000)
        for item in self.tree.get_children():
            self.tree.delete(item)
        for q in rows:
            self.tree.insert('', tk.END, values=(
                q.id or "",
                q.start_at.strftime("%Y-%m-%d %H:%M:%S"),
                q.call,
                q.band or "",
                q.mode or "",
                q.grid or "",
                (q.comment or "")[:60],
            ))

    def _delete_selected(self) -> None:
        """Delete highlighted QSOs from the Browse table after confirmation."""
        sel = self.tree.selection()
        if not sel:
            return
        if not messagebox.askyesno("Confirm", "Delete selected QSO(s)?"):
            return
        for item in sel:
            vals = self.tree.item(item, 'values')
            qso_id = int(vals[0])
            delete_qso(qso_id)
        self._refresh_table()

    # Awards tab
    def _build_awards_tab(self) -> None:
        """Create the "Awards" tab showing a summary and AI evaluation tools."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Awards")

        top = ttk.Frame(frame)
        top.pack(fill="x", padx=8, pady=6)

        ttk.Label(top, text="Band:").pack(side="left")
        self.a_band = ttk.Entry(top, width=10)
        self.a_band.pack(side="left", padx=6)

        ttk.Label(top, text="Mode:").pack(side="left")
        self.a_mode = ttk.Entry(top, width=10)
        self.a_mode.pack(side="left", padx=6)

        ttk.Button(top, text="Refresh", command=self._awards_refresh).pack(side="left", padx=6)

        self.awards_text = tk.Text(frame, height=10)
        self.awards_text.pack(fill="both", expand=False, padx=8, pady=4)

        # Evaluate section
        eval_frame = ttk.Frame(frame)
        eval_frame.pack(fill="x", padx=8, pady=6)
        ttk.Label(eval_frame, text="Goals:").pack(side="left")
        self.e_goals = ttk.Entry(eval_frame, width=50)
        self.e_goals.pack(side="left", padx=6)
        ttk.Button(eval_frame, text="Evaluate", command=self._awards_eval).pack(side="left", padx=6)

        self.eval_text = tk.Text(frame, height=10)
        self.eval_text.pack(fill="both", expand=True, padx=8, pady=4)

        self._awards_refresh()

    def _awards_refresh(self) -> None:
        """Compute and display the deterministic awards summary in the text box."""
        band = self.a_band.get() or None
        mode = self.a_mode.get() or None
        qsos = filtered_qsos(list_qsos(limit=10000), band=band, mode=mode)
        s = compute_summary(qsos)
        lines = [
            "Awards summary:",
            f"- Total QSOs: {s['total_qsos']}",
            f"- Unique countries: {s['unique_countries']}",
            f"- Unique grids: {s['unique_grids']}",
            f"- Unique calls: {s['unique_calls']}",
            f"- Unique bands: {s['unique_bands']} | modes: {s['unique_modes']}",
        ]
        gpb = s.get('grids_per_band', {}) or {}
        for b, c in sorted(gpb.items()):
            lines.append(f"- Grids on {b or 'unknown'}: {c}")
        self.awards_text.delete("1.0", tk.END)
        self.awards_text.insert(tk.END, "\n".join(lines))

    def _awards_eval(self) -> None:
        """Run the AI-assisted awards evaluation in a background thread."""
        band = self.a_band.get() or None
        mode = self.a_mode.get() or None
        goals = self.e_goals.get() or None
        qsos = filtered_qsos(list_qsos(limit=10000), band=band, mode=mode)
        self._run_in_thread(
            self.eval_text, "Evaluating...\n", evaluate_awards, qsos, goals=goals
        )

    # Tools tab
    def _build_tools_tab(self) -> None:
        """Create the "Tools" tab for ADIF import/export and quick summaries."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Tools")

        ttk.Label(frame, text=f"Database: {get_db_path()}").pack(anchor="w", padx=8, pady=6)

        btns = ttk.Frame(frame)
        btns.pack(fill="x", padx=8, pady=6)

        ttk.Button(btns, text="Export ADIF", command=self._export_adif).pack(side="left", padx=6)
        ttk.Button(btns, text="Import ADIF", command=self._import_adif).pack(side="left", padx=6)
        ttk.Button(btns, text="Summarize QSOs", command=self._summarize).pack(side="left", padx=6)

        self.tools_text = tk.Text(frame, height=12)
        self.tools_text.pack(fill="both", expand=True, padx=8, pady=6)

    def _export_adif(self) -> None:
        """Export recent QSOs to an ADIF file chosen by the user."""
        path = filedialog.asksaveasfilename(
            title="Export ADIF",
            defaultextension=".adi",
            filetypes=[("ADIF", ".adi"), ("All Files", "*.*")],
        )
        if not path:
            return
        qsos = list_qsos(limit=100000)
        txt = dump_adif(qsos)
        try:
            Path(path).write_text(txt, encoding="utf-8")
            messagebox.showinfo("Exported", f"Wrote {len(qsos)} QSOs to {path}")
        except (IOError, OSError, PermissionError) as e:
            messagebox.showerror("Error", str(e))

    def _import_adif(self) -> None:
        """Import QSOs from an ADIF file chosen by the user."""
        path = filedialog.askopenfilename(
            title="Import ADIF",
            filetypes=[("ADIF", ".adi"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
            qsos = load_adif(text)
            for q in qsos:
                q.call = q.call.upper()
                add_qso(q)
            messagebox.showinfo("Imported", f"Imported {len(qsos)} QSOs from {path}")
            self._refresh_table()
        except (IOError, OSError, PermissionError, ValueError) as e:
            messagebox.showerror("Error", str(e))

    def _summarize(self) -> None:
        """Summarize recent QSOs (AI-enabled) in the Tools tab text area."""
        rows = list_qsos(limit=100)
        self._run_in_thread(
            self.tools_text, "Summarizing...\n", summarize_qsos, rows
        )

    def _run_in_thread(
        self,
        target_widget: tk.Text,
        initial_message: str,
        func: Callable[..., str],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Run a function in a background thread and update a text widget safely.

        Args:
            target_widget: The tk.Text widget to update.
            initial_message: The message to display while running.
            func: The function to execute in the background.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.
        """
        target_widget.delete("1.0", tk.END)
        target_widget.insert(tk.END, initial_message)

        def worker() -> None:
            try:
                result = func(*args, **kwargs)
            except (ValueError, IOError, OSError, RuntimeError) as e:
                result = f"Error: {e}"
            # Ensure UI updates occur on the main thread
            def apply_result() -> None:
                target_widget.delete("1.0", tk.END)
                target_widget.insert(tk.END, result)
            self.root.after(0, apply_result)

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    """Entrypoint for launching the Tkinter GUI."""
    root = tk.Tk()
    # Prefer native theme if available
    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "xpnative" in style.theme_names():
            style.theme_use("xpnative")
    except tk.TclError:
        pass
    LoggerGUI(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()

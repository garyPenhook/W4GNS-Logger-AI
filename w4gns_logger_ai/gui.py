from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from .adif import dump_adif, load_adif
from .ai_helper import evaluate_awards, summarize_qsos
from .awards import compute_summary, filtered_qsos
from .models import QSO, now_utc
from .storage import (
    APP_NAME,
    add_qso,
    create_db_and_tables,
    delete_qso,
    get_db_path,
    list_qsos,
    search_qsos,
)


class LoggerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x600")
        create_db_and_tables()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._build_log_tab()
        self._build_browse_tab()
        self._build_awards_tab()
        self._build_tools_tab()

    # Log tab
    def _build_log_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Log")

        row = 0
        def add_field(label: str, width: int = 20) -> tk.Entry:
            nonlocal row
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W, padx=6, pady=4)
            e = ttk.Entry(frame, width=width)
            e.grid(row=row, column=1, sticky=tk.W, padx=6, pady=4)
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

        ttk.Label(frame, text="Comment").grid(row=row, column=0, sticky=tk.NW, padx=6, pady=4)
        self.t_comment = tk.Text(frame, width=40, height=4)
        self.t_comment.grid(row=row, column=1, sticky=tk.W, padx=6, pady=4)
        row += 1

        btn = ttk.Button(frame, text="Save QSO", command=self._save_qso)
        btn.grid(row=row, column=1, sticky=tk.W, padx=6, pady=8)

    def _save_qso(self) -> None:
        call = (self.e_call.get() or "").strip().upper()
        if not call:
            messagebox.showwarning("Missing", "Callsign is required")
            return
        def parse_float(s: str) -> Optional[float]:
            try:
                return float(s)
            except Exception:
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
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Browse")

        filters = ttk.Frame(frame)
        filters.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(filters, text="Call contains:").pack(side=tk.LEFT)
        self.f_call = ttk.Entry(filters, width=16)
        self.f_call.pack(side=tk.LEFT, padx=6)

        ttk.Label(filters, text="Band:").pack(side=tk.LEFT)
        self.f_band = ttk.Entry(filters, width=10)
        self.f_band.pack(side=tk.LEFT, padx=6)

        ttk.Label(filters, text="Mode:").pack(side=tk.LEFT)
        self.f_mode = ttk.Entry(filters, width=10)
        self.f_mode.pack(side=tk.LEFT, padx=6)

        ttk.Button(filters, text="Refresh", command=self._refresh_table).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(filters, text="Delete selected", command=self._delete_selected).pack(
            side=tk.LEFT, padx=6
        )

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
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        self._refresh_table()

    def _refresh_table(self) -> None:
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
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Awards")

        top = ttk.Frame(frame)
        top.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(top, text="Band:").pack(side=tk.LEFT)
        self.a_band = ttk.Entry(top, width=10)
        self.a_band.pack(side=tk.LEFT, padx=6)

        ttk.Label(top, text="Mode:").pack(side=tk.LEFT)
        self.a_mode = ttk.Entry(top, width=10)
        self.a_mode.pack(side=tk.LEFT, padx=6)

        ttk.Button(top, text="Refresh", command=self._awards_refresh).pack(
            side=tk.LEFT, padx=6
        )

        self.awards_text = tk.Text(frame, height=10)
        self.awards_text.pack(fill=tk.BOTH, expand=False, padx=8, pady=4)

        # Evaluate section
        eval_frame = ttk.Frame(frame)
        eval_frame.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(eval_frame, text="Goals:").pack(side=tk.LEFT)
        self.e_goals = ttk.Entry(eval_frame, width=50)
        self.e_goals.pack(side=tk.LEFT, padx=6)
        ttk.Button(eval_frame, text="Evaluate", command=self._awards_eval).pack(
            side=tk.LEFT, padx=6
        )

        self.eval_text = tk.Text(frame, height=10)
        self.eval_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._awards_refresh()

    def _awards_refresh(self) -> None:
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
        band = self.a_band.get() or None
        mode = self.a_mode.get() or None
        goals = self.e_goals.get() or None
        qsos = filtered_qsos(list_qsos(limit=10000), band=band, mode=mode)
        self.eval_text.delete("1.0", tk.END)
        self.eval_text.insert(tk.END, "Evaluating...\n")

        def run():
            try:
                text = evaluate_awards(qsos, goals=goals)
            except Exception as e:
                text = f"Error: {e}"
            self.eval_text.delete("1.0", tk.END)
            self.eval_text.insert(tk.END, text)

        threading.Thread(target=run, daemon=True).start()

    # Tools tab
    def _build_tools_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Tools")

        ttk.Label(frame, text=f"Database: {get_db_path()}").pack(anchor=tk.W, padx=8, pady=6)

        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(btns, text="Export ADIF", command=self._export_adif).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Import ADIF", command=self._import_adif).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Summarize QSOs", command=self._summarize).pack(side=tk.LEFT, padx=6)

        self.tools_text = tk.Text(frame, height=12)
        self.tools_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

    def _export_adif(self) -> None:
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
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _import_adif(self) -> None:
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
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _summarize(self) -> None:
        self.tools_text.delete("1.0", tk.END)
        self.tools_text.insert(tk.END, "Summarizing...\n")

        def run():
            try:
                rows = list_qsos(limit=100)
                text = summarize_qsos(rows)
            except Exception as e:
                text = f"Error: {e}"
            self.tools_text.delete("1.0", tk.END)
            self.tools_text.insert(tk.END, text)

        threading.Thread(target=run, daemon=True).start()


def main() -> None:
    root = tk.Tk()
    # Prefer native theme if available
    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "xpnative" in style.theme_names():
            style.theme_use("xpnative")
    except Exception:
        pass
    LoggerGUI(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover
    main()

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from platformdirs import user_config_dir

from .models import QSO


def _norm(s: Optional[str]) -> Optional[str]:
    return s.strip().upper() if isinstance(s, str) and s.strip() else None


def unique_values(qsos: Iterable[QSO], attr: str) -> Set[str]:
    out: Set[str] = set()
    for q in qsos:
        v = getattr(q, attr, None)
        nv = _norm(v)
        if nv:
            out.add(nv)
    return out


def unique_by_band(qsos: Iterable[QSO], attr: str) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = defaultdict(set)
    for q in qsos:
        band = _norm(getattr(q, "band", None)) or ""
        v = getattr(q, attr, None)
        nv = _norm(v)
        if nv:
            out[band].add(nv)
    return out


def compute_summary(qsos: Iterable[QSO]) -> Dict[str, object]:
    qsos = list(qsos)
    total = len(qsos)

    countries = unique_values(qsos, "country")
    grids = unique_values(qsos, "grid")
    calls = unique_values(qsos, "call")
    bands = unique_values(qsos, "band")
    modes = unique_values(qsos, "mode")

    grids_by_band = {b or "": len(vs) for b, vs in unique_by_band(qsos, "grid").items()}

    return {
        "total_qsos": total,
        "unique_countries": len(countries),
        "unique_grids": len(grids),
        "unique_calls": len(calls),
        "unique_bands": len(bands),
        "unique_modes": len(modes),
        "grids_per_band": grids_by_band,
    }


# Default thresholds; can be overridden via config
DEFAULT_AWARD_THRESHOLDS: Dict[str, int] = {
    "DXCC": 100,  # unique countries
    "VUCC": 100,  # unique grids (band-specific often)
}

CONFIG_ENV_VAR = "W4GNS_AWARDS_CONFIG"
CONFIG_FILENAME = "awards.json"


def _config_path() -> Path:
    env = os.getenv(CONFIG_ENV_VAR)
    if env:
        return Path(env).expanduser()
    cfg_dir = Path(user_config_dir(appname="W4GNS Logger AI", appauthor=False))
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / CONFIG_FILENAME


def get_award_thresholds() -> Dict[str, int]:
    """Load thresholds from JSON, overriding defaults.

    JSON shape: { "DXCC": 125, "VUCC": 75, "MY_CUSTOM": 50 }
    """
    p = _config_path()
    data: Dict[str, int] = dict(DEFAULT_AWARD_THRESHOLDS)
    try:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, dict):
                    for k, v in raw.items():
                        if isinstance(k, str) and isinstance(v, int) and v > 0:
                            data[k.upper()] = v
    except Exception:
        # Ignore malformed configs; fall back to defaults
        pass
    return data


def suggest_awards(summary: Dict[str, object]) -> List[str]:
    thresholds = get_award_thresholds()
    suggestions: List[str] = []
    countries = int(summary.get("unique_countries", 0) or 0)
    grids = int(summary.get("unique_grids", 0) or 0)

    dxcc_needed = thresholds.get("DXCC", DEFAULT_AWARD_THRESHOLDS["DXCC"])
    vucc_needed = thresholds.get("VUCC", DEFAULT_AWARD_THRESHOLDS["VUCC"])

    if countries >= dxcc_needed:
        suggestions.append(f"DXCC achieved: {countries} unique countries")
    elif countries >= int(0.9 * dxcc_needed):
        remaining = dxcc_needed - countries
        suggestions.append(f"DXCC close: {countries} countries (need {remaining} more)")

    if grids >= vucc_needed:
        suggestions.append(f"VUCC achieved: {grids} unique grids")
    elif grids >= int(0.9 * vucc_needed):
        remaining = vucc_needed - grids
        suggestions.append(f"VUCC close: {grids} grids (need {remaining} more)")

    # Band-specific VUCC hints
    gpb = summary.get("grids_per_band", {}) or {}
    if isinstance(gpb, dict):
        for band, count in sorted(gpb.items()):
            c = int(count or 0)
            if c >= 50:
                suggestions.append(f"Strong grid count on {band or 'unknown'}: {c}")
    return suggestions


def filtered_qsos(
    qsos: Iterable[QSO],
    *,
    band: Optional[str] = None,
    mode: Optional[str] = None,
) -> List[QSO]:
    qsos = list(qsos)
    b = _norm(band) if band else None
    m = _norm(mode) if mode else None
    out: List[QSO] = []
    for q in qsos:
        if b and _norm(q.band) != b:
            continue
        if m and _norm(q.mode) != m:
            continue
        out.append(q)
    return out

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set

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


# Heuristic award thresholds (approximate), can be refined later
AWARD_THRESHOLDS = {
    "DXCC": 100,  # unique countries
    "VUCC": 100,  # unique grids (band-specific often)
}


def suggest_awards(summary: Dict[str, object]) -> List[str]:
    suggestions: List[str] = []
    countries = int(summary.get("unique_countries", 0) or 0)
    grids = int(summary.get("unique_grids", 0) or 0)

    if countries >= AWARD_THRESHOLDS["DXCC"]:
        suggestions.append(f"DXCC achieved: {countries} unique countries")
    elif countries >= int(0.9 * AWARD_THRESHOLDS["DXCC"]):
        remaining = AWARD_THRESHOLDS["DXCC"] - countries
        suggestions.append(f"DXCC close: {countries} countries (need {remaining} more)")

    if grids >= AWARD_THRESHOLDS["VUCC"]:
        suggestions.append(f"VUCC achieved: {grids} unique grids")
    elif grids >= int(0.9 * AWARD_THRESHOLDS["VUCC"]):
        remaining = AWARD_THRESHOLDS["VUCC"] - grids
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

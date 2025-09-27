"""AI-powered helpers for summaries and awards evaluation.

These helpers use OpenAI if an API key is present and the optional 'ai' extras
are installed. If not, they degrade gracefully to fast, local fallbacks.
"""

from __future__ import annotations

from typing import Iterable

from .awards import compute_summary, suggest_awards
from .models import QSO


def _fallback_summary(qsos: Iterable[QSO]) -> str:
    """Produce a compact local summary when AI is unavailable.

    Includes counts of QSOs, unique calls, bands, and modes.
    """
    qsos = list(qsos)
    if not qsos:
        return "No QSOs to summarize."
    calls = {q.call for q in qsos}
    bands = {q.band for q in qsos if q.band}
    modes = {q.mode for q in qsos if q.mode}
    return (
        f"QSOs: {len(qsos)} | Calls: {len(calls)} | "
        f"Bands: {', '.join(sorted(bands)) if bands else 'n/a'} | "
        f"Modes: {', '.join(sorted(modes)) if modes else 'n/a'}"
    )


def summarize_qsos(qsos: Iterable[QSO], *, model: str = "gpt-4o-mini") -> str:
    """Summarize recent QSOs using OpenAI, with a robust local fallback.

    Set environment variable OPENAI_API_KEY to enable the cloud path.
    The response is intentionally short and actionable for operators.
    """
    try:
        import os

        from openai import OpenAI  # type: ignore

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return _fallback_summary(list(qsos))
        client = OpenAI(api_key=api_key)
        # Build concise bullet list of the most recent QSOs
        lines = []
        for q in list(qsos)[:50]:
            parts = [q.start_at.strftime("%Y-%m-%d %H:%MZ"), q.call]
            if q.band:
                parts.append(q.band)
            if q.mode:
                parts.append(q.mode)
            if q.grid:
                parts.append(q.grid)
            lines.append(" | ".join(parts))
        prompt = (
            "You are an assistant for a ham radio QSO log. Summarize these recent QSOs "
            "into 2-4 short bullet points, highlighting bands, modes, notable DX, and patterns.\n\n"
            + "\n".join(lines)
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        # Any failure falls back to local summary
        return _fallback_summary(list(qsos))


def evaluate_awards(
    qsos: Iterable[QSO],
    goals: str | None = None,
    *,
    model: str = "gpt-4o-mini",
) -> str:
    """Evaluate awards progress and produce a short plan.

    If OpenAI is configured, we provide tailored guidance based on a compact
    deterministic summary. Otherwise, we return the deterministic baseline.
    """
    qsos_list = list(qsos)
    summary = compute_summary(qsos_list)
    base_suggestions = suggest_awards(summary)
    base_text = [
        "Awards summary:",
        f"- QSOs: {summary['total_qsos']}",
        f"- Unique countries: {summary['unique_countries']}",
        f"- Unique grids: {summary['unique_grids']}",
        f"- Bands: {summary['unique_bands']} | Modes: {summary['unique_modes']}",
    ]
    if base_suggestions:
        base_text.append("Suggestions:")
        base_text.extend(f"- {s}" for s in base_suggestions)
    else:
        base_text.append("Suggestions: none yet — keep logging!")

    try:
        import os

        from openai import OpenAI  # type: ignore

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "\n".join(base_text)
        client = OpenAI(api_key=api_key)
        # Keep content compact; include deterministic baseline
        content_lines = base_text + [
            "",
            "Provide a short, actionable plan (3-6 bullets) to reach awards goals.",
            (
                "Be specific about band/mode focus, missing entities (countries/grids), "
                "and operating tips."
            ),
        ]
        if goals:
            content_lines.append(f"User goals: {goals}")
        prompt = "\n".join(content_lines)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "\n".join(base_text)

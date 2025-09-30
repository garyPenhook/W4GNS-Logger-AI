"""AI-powered helper functions for summarizing QSOs and evaluating awards progress.

When OpenAI is configured via OPENAI_API_KEY, we use GPT models for enhanced insights.
Otherwise, we fall back to deterministic, local-only approaches.

Enhanced with concurrent processing for improved performance.
"""

from __future__ import annotations

import concurrent.futures
import os
from typing import Iterable, List

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
        import openai

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return _fallback_summary(list(qsos))
        client = openai.OpenAI(api_key=api_key)
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
    except (ImportError, AttributeError, ValueError, ConnectionError, TimeoutError):
        # Any failure falls back to local summary
        return _fallback_summary(list(qsos))


def summarize_qsos_parallel(
    qsos_batches: List[List[QSO]], *, model: str = "gpt-4o-mini"
) -> List[str]:
    """Summarize multiple batches of QSOs concurrently using OpenAI.

    Processes multiple QSO batches in parallel for improved performance.
    Each batch is summarized independently and results are combined.

    Args:
        qsos_batches: List of QSO batches to process
        model: OpenAI model to use

    Returns:
        List of summary strings, one per batch
    """
    try:
        import openai

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return [_fallback_summary(batch) for batch in qsos_batches]

        client = openai.OpenAI(api_key=api_key)

        def process_batch(qsos: List[QSO]) -> str:
            try:
                # Build concise bullet list of QSOs
                lines = []
                for q in qsos[:50]:  # Limit per batch
                    parts = [q.start_at.strftime("%Y-%m-%d %H:%MZ"), q.call]
                    if q.band:
                        parts.append(q.band)
                    if q.mode:
                        parts.append(q.mode)
                    if q.grid:
                        parts.append(q.grid)
                    lines.append(" | ".join(parts))

                prompt = (
                    "You are an assistant for a ham radio QSO log. Summarize these QSOs "
                    "into 2-4 short bullet points, highlighting bands, modes, "
                    "notable DX, and patterns.\n\n"
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
                return _fallback_summary(qsos)

        # Use conservative worker count for CI compatibility
        is_ci = any(env in os.environ for env in ['CI', 'GITHUB_ACTIONS', 'TRAVIS', 'JENKINS'])
        max_workers = 2 if is_ci else 5

        # Process batches concurrently
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_batch, batch) for batch in qsos_batches]
                results = []
                for future in concurrent.futures.as_completed(futures, timeout=60):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception:
                        results.append(_fallback_summary([]))
                return results
        except concurrent.futures.TimeoutError:
            # Fallback on timeout
            return [_fallback_summary(batch) for batch in qsos_batches]

    except (ImportError, AttributeError, ValueError, ConnectionError, TimeoutError):
        # Fall back to local summaries
        return [_fallback_summary(batch) for batch in qsos_batches]


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
        import openai

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "\n".join(base_text)
        client = openai.OpenAI(api_key=api_key)
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
    except (ImportError, AttributeError, ValueError, ConnectionError, TimeoutError):
        return "\n".join(base_text)


def evaluate_awards_concurrent(
    qsos_groups: List[List[QSO]],
    goals: str | None = None,
    *,
    model: str = "gpt-4o-mini",
) -> List[str]:
    """Evaluate awards progress for multiple QSO groups concurrently.

    Processes multiple groups of QSOs in parallel for comprehensive analysis.
    Useful for analyzing awards progress across different bands/modes simultaneously.

    Args:
        qsos_groups: List of QSO groups to analyze
        goals: User's awards goals
        model: OpenAI model to use

    Returns:
        List of evaluation results, one per group
    """
    def process_group(qsos: List[QSO]) -> str:
        return evaluate_awards(qsos, goals, model=model)

    # Use conservative settings for CI environments
    is_ci = any(env in os.environ for env in ['CI', 'GITHUB_ACTIONS', 'TRAVIS', 'JENKINS'])
    max_workers = 2 if is_ci else 3

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_group, group) for group in qsos_groups]
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=120):
                try:
                    result = future.result()
                    results.append(result)
                except Exception:
                    # Fallback for failed group
                    results.append("Error processing awards evaluation")
            return results
    except (Exception, concurrent.futures.TimeoutError):
        # Fall back to sequential processing
        return [process_group(group) for group in qsos_groups]

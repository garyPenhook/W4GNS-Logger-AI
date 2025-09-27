from datetime import datetime

from w4gns_logger_ai.awards import (
    compute_summary,
    filtered_qsos,
    suggest_awards,
    get_award_thresholds,
    compute_summary_parallel,
)
from w4gns_logger_ai.models import QSO


def test_compute_summary_basic():
    """Test basic awards summary computation."""
    qsos = [
        QSO(call="K1ABC", start_at=datetime(2024, 1, 1), country="USA", grid="FN42", band="20m", mode="SSB"),
        QSO(call="G0XYZ", start_at=datetime(2024, 1, 2), country="England", grid="IO91", band="40m", mode="CW"),
        QSO(call="JA1DEF", start_at=datetime(2024, 1, 3), country="Japan", grid="PM95", band="20m", mode="FT8"),
    ]

    summary = compute_summary(qsos)

    assert summary["total_qsos"] == 3
    assert summary["unique_countries"] == 3
    assert summary["unique_grids"] == 3
    assert summary["unique_calls"] == 3
    assert summary["unique_bands"] == 2
    assert summary["unique_modes"] == 3
    assert isinstance(summary["grids_per_band"], dict)


def test_filtered_qsos():
    """Test QSO filtering by band and mode."""
    qsos = [
        QSO(call="K1ABC", start_at=datetime(2024, 1, 1), band="20m", mode="SSB"),
        QSO(call="G0XYZ", start_at=datetime(2024, 1, 2), band="40m", mode="CW"),
        QSO(call="JA1DEF", start_at=datetime(2024, 1, 3), band="20m", mode="FT8"),
    ]

    # Filter by band
    filtered_20m = filtered_qsos(qsos, band="20m")
    assert len(filtered_20m) == 2
    assert all(q.band == "20m" for q in filtered_20m)

    # Filter by mode
    filtered_ssb = filtered_qsos(qsos, mode="SSB")
    assert len(filtered_ssb) == 1
    assert filtered_ssb[0].mode == "SSB"

    # Filter by both
    filtered_both = filtered_qsos(qsos, band="20m", mode="FT8")
    assert len(filtered_both) == 1
    assert filtered_both[0].call == "JA1DEF"


def test_suggest_awards():
    """Test award suggestions."""
    # Create summary with enough countries for DXCC
    summary = {
        "total_qsos": 150,
        "unique_countries": 105,
        "unique_grids": 50,
        "unique_calls": 140,
        "unique_bands": 5,
        "unique_modes": 4,
        "grids_per_band": {"20m": 60, "40m": 45}
    }

    suggestions = suggest_awards(summary)
    assert len(suggestions) > 0
    assert any("DXCC achieved" in s for s in suggestions)
    assert any("Strong grid count" in s for s in suggestions)


def test_get_award_thresholds():
    """Test award thresholds loading."""
    thresholds = get_award_thresholds()
    assert isinstance(thresholds, dict)
    assert "DXCC" in thresholds
    assert "VUCC" in thresholds
    assert thresholds["DXCC"] > 0
    assert thresholds["VUCC"] > 0


def test_parallel_summary_small_dataset():
    """Test that small datasets use sequential processing."""
    qsos = [
        QSO(call="K1ABC", start_at=datetime(2024, 1, 1), country="USA"),
        QSO(call="G0XYZ", start_at=datetime(2024, 1, 2), country="England"),
    ]

    # Should use sequential processing for small datasets
    summary = compute_summary_parallel(qsos, chunk_size=1000)
    assert summary["total_qsos"] == 2
    assert summary["unique_countries"] == 2

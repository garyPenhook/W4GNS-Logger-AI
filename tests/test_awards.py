from datetime import datetime

from w4gns_logger_ai.awards import compute_summary, filtered_qsos, suggest_awards
from w4gns_logger_ai.models import QSO


def sample_qsos():
    return [
        QSO(
            call="K1AAA",
            start_at=datetime(2024, 1, 1),
            band="20m",
            mode="SSB",
            grid="FN42",
            country="USA",
        ),
        QSO(
            call="DL1BBB",
            start_at=datetime(2024, 1, 2),
            band="20m",
            mode="SSB",
            grid="JO62",
            country="GERMANY",
        ),
        QSO(
            call="JA1CCC",
            start_at=datetime(2024, 1, 3),
            band="15m",
            mode="CW",
            grid="PM95",
            country="JAPAN",
        ),
        QSO(
            call="K1AAA",
            start_at=datetime(2024, 1, 4),
            band="40m",
            mode="FT8",
            grid="FN42",
            country="USA",
        ),
    ]


def test_compute_summary_and_filter():
    qsos = sample_qsos()
    s = compute_summary(qsos)
    assert s["total_qsos"] == 4
    assert s["unique_countries"] == 3
    assert s["unique_grids"] == 3
    assert s["unique_calls"] == 3
    assert s["unique_bands"] == 3
    assert s["unique_modes"] == 3
    gpb = s["grids_per_band"]
    # 20m: FN42 + JO62, 15m: PM95, 40m: FN42
    assert gpb["20M"] == 2
    assert gpb["15M"] == 1
    assert gpb["40M"] == 1

    # Filtering
    only_20m = filtered_qsos(qsos, band="20m")
    assert len(only_20m) == 2
    only_ssb = filtered_qsos(qsos, mode="SSB")
    assert len(only_ssb) == 2


def test_suggest_awards():
    qsos = sample_qsos()
    s = compute_summary(qsos)
    suggestions = suggest_awards(s)
    # With small dataset, we expect no DXCC/VUCC achievement or close notice
    assert all("DXCC" not in x for x in suggestions)
    assert all("VUCC" not in x for x in suggestions)

import json
from datetime import datetime

from w4gns_logger_ai.awards import CONFIG_ENV_VAR, compute_summary, suggest_awards
from w4gns_logger_ai.models import QSO


def test_awards_threshold_override(tmp_path, monkeypatch):
    # Create a custom config threshold file
    cfg = tmp_path / "awards.json"
    cfg.write_text(json.dumps({"DXCC": 2, "VUCC": 2}), encoding="utf-8")
    monkeypatch.setenv(CONFIG_ENV_VAR, str(cfg))

    # Make 2 unique countries and 2 unique grids
    qsos = [
        QSO(call="K1AAA", start_at=datetime(2024, 1, 1), country="USA", grid="FN42"),
        QSO(call="DL1BBB", start_at=datetime(2024, 1, 2), country="GERMANY", grid="JO62"),
    ]
    s = compute_summary(qsos)
    suggestions = suggest_awards(s)
    # With thresholds at 2, both achievements should be detected
    assert any("DXCC achieved" in x for x in suggestions)
    assert any("VUCC achieved" in x for x in suggestions)

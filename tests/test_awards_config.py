import json
import tempfile
from pathlib import Path

from w4gns_logger_ai.awards import get_award_thresholds


def test_default_thresholds():
    """Test that default award thresholds are loaded when no config exists."""
    thresholds = get_award_thresholds()
    assert "DXCC" in thresholds
    assert "VUCC" in thresholds
    assert thresholds["DXCC"] == 100
    assert thresholds["VUCC"] == 100


def test_custom_thresholds(tmp_path, monkeypatch):
    """Test loading custom thresholds from config file."""
    # Create a custom config file
    config_path = tmp_path / "awards.json"
    custom_config = {
        "DXCC": 150,
        "VUCC": 75,
        "CUSTOM_AWARD": 50
    }

    with open(config_path, "w") as f:
        json.dump(custom_config, f)

    # Mock the environment variable to point to our test config
    monkeypatch.setenv("W4GNS_AWARDS_CONFIG", str(config_path))

    # Clear any cached config by reimporting
    import importlib
    import w4gns_logger_ai.awards
    importlib.reload(w4gns_logger_ai.awards)

    thresholds = w4gns_logger_ai.awards.get_award_thresholds()

    assert thresholds["DXCC"] == 150
    assert thresholds["VUCC"] == 75
    assert thresholds["CUSTOM_AWARD"] == 50


def test_malformed_config_fallback(tmp_path, monkeypatch):
    """Test that malformed config files fall back to defaults."""
    # Create a malformed config file
    config_path = tmp_path / "bad_awards.json"
    with open(config_path, "w") as f:
        f.write("{ invalid json }")

    # Mock the environment variable
    monkeypatch.setenv("W4GNS_AWARDS_CONFIG", str(config_path))

    # Clear any cached config
    import importlib
    import w4gns_logger_ai.awards
    importlib.reload(w4gns_logger_ai.awards)

    thresholds = w4gns_logger_ai.awards.get_award_thresholds()

    # Should fall back to defaults
    assert thresholds["DXCC"] == 100
    assert thresholds["VUCC"] == 100

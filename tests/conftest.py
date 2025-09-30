import pytest


@pytest.fixture
def sample_qso():
    """Create a sample QSO for testing."""
    from datetime import datetime

    from w4gns_logger_ai.models import QSO

    return QSO(
        call="K1ABC",
        start_at=datetime(2024, 7, 4, 12, 0, 0),
        band="20m",
        mode="SSB",
        freq_mhz=14.250,
        rst_sent="59",
        rst_rcvd="59",
        name="Test",
        qth="Test City",
        grid="FN42",
        country="USA",
        comment="Test QSO"
    )


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    import os

    # Store original value if it exists
    original_db_path = os.environ.get("W4GNS_DB_PATH")

    # Set temporary database path
    db_path = tmp_path / "test.sqlite3"
    os.environ["W4GNS_DB_PATH"] = str(db_path)

    try:
        from w4gns_logger_ai.storage import create_db_and_tables
        create_db_and_tables()

        yield db_path

    finally:
        # Cleanup - restore original value or remove if it wasn't set
        if original_db_path:
            os.environ["W4GNS_DB_PATH"] = original_db_path
        elif "W4GNS_DB_PATH" in os.environ:
            del os.environ["W4GNS_DB_PATH"]

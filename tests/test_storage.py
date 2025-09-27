import tempfile
from pathlib import Path

from w4gns_logger_ai.models import QSO
from w4gns_logger_ai.storage import (
    add_qso,
    create_db_and_tables,
    delete_qso,
    get_qso,
    list_qsos,
    search_qsos,
    bulk_add_qsos,
)


def test_storage_basic_crud(tmp_path):
    """Test basic CRUD operations."""
    import os
    # Use temporary database for testing
    os.environ["W4GNS_DB_PATH"] = str(tmp_path / "test.sqlite3")

    # Create tables
    create_db_and_tables()

    # Test adding a QSO
    from datetime import datetime
    qso = QSO(
        call="K1ABC",
        start_at=datetime(2024, 7, 4, 12, 0, 0),
        band="20m",
        mode="SSB"
    )

    saved_qso = add_qso(qso)
    assert saved_qso.id is not None
    assert saved_qso.call == "K1ABC"

    # Test retrieving the QSO
    retrieved = get_qso(saved_qso.id)
    assert retrieved is not None
    assert retrieved.call == "K1ABC"

    # Test listing QSOs
    qsos = list_qsos(limit=10)
    assert len(qsos) == 1
    assert qsos[0].call == "K1ABC"

    # Test searching QSOs
    results = search_qsos(call="K1ABC")
    assert len(results) == 1
    assert results[0].call == "K1ABC"

    # Test deleting the QSO
    deleted = delete_qso(saved_qso.id)
    assert deleted is True

    # Verify deletion
    retrieved = get_qso(saved_qso.id)
    assert retrieved is None


def test_bulk_operations(tmp_path):
    """Test bulk operations."""
    import os
    from datetime import datetime

    # Use temporary database for testing
    os.environ["W4GNS_DB_PATH"] = str(tmp_path / "test_bulk.sqlite3")

    # Create tables
    create_db_and_tables()

    # Create multiple QSOs
    qsos = []
    for i in range(10):
        qso = QSO(
            call=f"K1ABC{i}",
            start_at=datetime(2024, 7, 4, 12, i, 0),
            band="20m",
            mode="SSB"
        )
        qsos.append(qso)

    # Test bulk add
    count = bulk_add_qsos(qsos)
    assert count == 10

    # Verify they were added
    all_qsos = list_qsos(limit=20)
    assert len(all_qsos) == 10

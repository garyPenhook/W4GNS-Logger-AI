import pytest

from w4gns_logger_ai.storage import DB_ENV_VAR, create_db_and_tables


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    # Use a temp DB per test session
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setenv(DB_ENV_VAR, str(db_path))
    create_db_and_tables()
    yield
    # no explicit teardown needed; file is in tmp_path

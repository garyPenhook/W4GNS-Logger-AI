from datetime import datetime

from w4gns_logger_ai.models import QSO
from w4gns_logger_ai.storage import add_qso, delete_qso, list_qsos, search_qsos


def test_add_list_delete_and_search():
    q1 = QSO(call="K1ABC", start_at=datetime(2024, 1, 1, 0, 0), band="20m", mode="SSB", grid="FN42")
    q2 = QSO(call="DL1XYZ", start_at=datetime(2024, 1, 2, 0, 0), band="40m", mode="CW", grid="JO62")
    add_qso(q1)
    add_qso(q2)

    rows = list_qsos(limit=10)
    assert len(rows) == 2

    # Search by fields
    s1 = search_qsos(call="K1")
    assert len(s1) == 1 and s1[0].call == "K1ABC"

    s2 = search_qsos(band="40m")
    assert len(s2) == 1 and s2[0].call == "DL1XYZ"

    s3 = search_qsos(mode="CW")
    assert len(s3) == 1 and s3[0].call == "DL1XYZ"

    s4 = search_qsos(grid="FN42")
    assert len(s4) == 1 and s4[0].call == "K1ABC"

    # Delete and verify
    assert delete_qso(rows[0].id)
    assert len(list_qsos(limit=10)) == 1


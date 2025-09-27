from datetime import datetime

from w4gns_logger_ai.adif import dump_adif, load_adif
from w4gns_logger_ai.models import QSO


def test_adif_roundtrip_basic():
    q = QSO(
        call="K1ABC",
        start_at=datetime(2024, 7, 4, 12, 34, 56),
        band="20m",
        mode="SSB",
        freq_mhz=14.250,
        rst_sent="59",
        rst_rcvd="59",
        name="Alice",
        qth="Boston",
        grid="FN42",
        country="USA",
        comment="Holiday activation",
    )
    txt = dump_adif([q])
    parsed = load_adif(txt)
    assert len(parsed) == 1
    p = parsed[0]
    assert p.call == q.call
    assert p.start_at == q.start_at
    assert p.band == q.band
    assert p.mode == q.mode
    assert abs((p.freq_mhz or 0) - (q.freq_mhz or 0)) < 1e-6
    assert p.rst_sent == q.rst_sent
    assert p.rst_rcvd == q.rst_rcvd
    assert p.name == q.name
    assert p.qth == q.qth
    assert p.grid == q.grid
    assert p.country == q.country
    assert p.comment == q.comment


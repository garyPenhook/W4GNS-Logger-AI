from datetime import datetime

from w4gns_logger_ai.adif import dump_adif, load_adif
from w4gns_logger_ai.models import QSO


def test_adif_roundtrip_basic():
    """Test basic ADIF export/import roundtrip."""
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


def test_adif_empty():
    """Test empty ADIF input."""
    parsed = load_adif("")
    assert parsed == []


def test_adif_malformed():
    """Test that malformed ADIF doesn't crash."""
    malformed = "<CALL:5>K1ABC<QSO_DATE:8>20240704<EOR>"  # Missing TIME_ON
    parsed = load_adif(malformed)
    assert len(parsed) == 0  # Should skip invalid records


def test_adif_parallel_processing():
    """Test that parallel ADIF processing works for large datasets."""
    from w4gns_logger_ai.adif import load_adif_parallel

    # Create a large ADIF string
    qsos_data = []
    for i in range(200):  # Enough to trigger parallel processing
        qsos_data.append(f"<CALL:6>K1ABC{i}<QSO_DATE:8>20240704<TIME_ON:6>123456<EOR>")

    adif_text = "<ADIF_VER:3>3.1<EOH>" + "".join(qsos_data)

    # Test parallel processing
    parsed = load_adif_parallel(adif_text)
    assert len(parsed) == 200
    assert all(qso.call.startswith("K1ABC") for qso in parsed)

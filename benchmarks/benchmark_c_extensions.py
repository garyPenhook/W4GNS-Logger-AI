"""Benchmark suite for C extensions vs pure Python performance.

Run this after building C extensions to measure actual speedups.
"""

import time
from datetime import datetime
from typing import List

from w4gns_logger_ai.models import QSO


def generate_test_data(count: int = 10000) -> List[QSO]:
    """Generate synthetic QSO data for benchmarking."""
    qsos = []
    for i in range(count):
        qsos.append(
            QSO(
                call=f"W{i % 10}ABC",
                start_at=datetime(2025, 1, 1, 12, 0, 0),
                band=["20M", "40M", "80M", "10M"][i % 4],
                mode=["SSB", "CW", "FT8"][i % 3],
                freq_mhz=14.200 + (i % 100) * 0.001,
                rst_sent="59",
                rst_rcvd="59",
                name=f"Operator{i % 100}",
                qth=f"City{i % 50}",
                grid=f"FN{20 + i % 10}{30 + i % 10}",
                country=["USA", "Canada", "Mexico", "Germany"][i % 4],
                comment=f"Test QSO {i}",
            )
        )
    return qsos


def generate_adif_text(qsos: List[QSO]) -> str:
    """Generate ADIF text from QSO list."""
    lines = ["<ADIF_VER:3>3.1\n", "<PROGRAMID:13>W4GNS Logger\n", "<EOH>\n"]

    for q in qsos:
        dt = q.start_at
        date = dt.strftime("%Y%m%d")
        time_str = dt.strftime("%H%M%S")

        record = f"<QSO_DATE:8>{date}<TIME_ON:6>{time_str}<CALL:{len(q.call)}>{q.call}"
        if q.band:
            record += f"<BAND:{len(q.band)}>{q.band}"
        if q.mode:
            record += f"<MODE:{len(q.mode)}>{q.mode}"
        if q.freq_mhz:
            freq_str = f"{q.freq_mhz:.6f}".rstrip("0").rstrip(".")
            record += f"<FREQ:{len(freq_str)}>{freq_str}"
        if q.rst_sent:
            record += f"<RST_SENT:{len(q.rst_sent)}>{q.rst_sent}"
        if q.rst_rcvd:
            record += f"<RST_RCVD:{len(q.rst_rcvd)}>{q.rst_rcvd}"
        if q.name:
            record += f"<NAME:{len(q.name)}>{q.name}"
        if q.qth:
            record += f"<QTH:{len(q.qth)}>{q.qth}"
        if q.grid:
            record += f"<GRIDSQUARE:{len(q.grid)}>{q.grid}"
        if q.country:
            record += f"<COUNTRY:{len(q.country)}>{q.country}"
        if q.comment:
            record += f"<COMMENT:{len(q.comment)}>{q.comment}"
        record += "<EOR>\n"
        lines.append(record)

    return "".join(lines)


def benchmark_adif_parsing(adif_text: str, iterations: int = 10):
    """Benchmark ADIF parsing performance."""
    from w4gns_logger_ai import adif

    print(f"\n{'='*60}")
    print("ADIF PARSING BENCHMARK")
    print(f"{'='*60}")
    print(f"Text size: {len(adif_text):,} bytes")
    print(f"Iterations: {iterations}")

    # Measure parsing time
    start = time.time()
    for _ in range(iterations):
        qsos = adif.load_adif(adif_text)
    end = time.time()

    total_time = end - start
    avg_time = total_time / iterations
    qsos_per_sec = len(qsos) / avg_time if avg_time > 0 else 0

    print("\nResults:")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Average time: {avg_time:.3f}s per iteration")
    print(f"  QSOs parsed: {len(qsos):,}")
    print(f"  Throughput: {qsos_per_sec:,.0f} QSOs/sec")

    return avg_time


def benchmark_awards_computation(qsos: List[QSO], iterations: int = 10):
    """Benchmark awards computation performance."""
    from w4gns_logger_ai import awards

    print(f"\n{'='*60}")
    print("AWARDS COMPUTATION BENCHMARK")
    print(f"{'='*60}")
    print(f"QSO count: {len(qsos):,}")
    print(f"Iterations: {iterations}")

    # Measure computation time
    start = time.time()
    for _ in range(iterations):
        summary = awards.compute_summary_parallel(qsos)
    end = time.time()

    total_time = end - start
    avg_time = total_time / iterations
    qsos_per_sec = len(qsos) / avg_time if avg_time > 0 else 0

    print("\nResults:")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Average time: {avg_time:.3f}s per iteration")
    print(f"  Throughput: {qsos_per_sec:,.0f} QSOs/sec")
    print("\nSummary stats:")
    print(f"  Countries: {summary['unique_countries']}")
    print(f"  Grids: {summary['unique_grids']}")
    print(f"  Calls: {summary['unique_calls']}")

    return avg_time


def benchmark_adif_export(qsos: List[QSO], iterations: int = 10):
    """Benchmark ADIF export performance."""
    from w4gns_logger_ai import adif

    print(f"\n{'='*60}")
    print("ADIF EXPORT BENCHMARK")
    print(f"{'='*60}")
    print(f"QSO count: {len(qsos):,}")
    print(f"Iterations: {iterations}")

    # Measure export time
    start = time.time()
    for _ in range(iterations):
        text = adif.dump_adif(qsos)
    end = time.time()

    total_time = end - start
    avg_time = total_time / iterations
    qsos_per_sec = len(qsos) / avg_time if avg_time > 0 else 0

    print("\nResults:")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Average time: {avg_time:.3f}s per iteration")
    print(f"  Output size: {len(text):,} bytes")
    print(f"  Throughput: {qsos_per_sec:,.0f} QSOs/sec")

    return avg_time


def main():
    """Run all benchmarks."""
    print("="*60)
    print("W4GNS Logger C Extension Benchmark Suite")
    print("="*60)

    # Check if C extensions are available
    from w4gns_logger_ai import adif

    if hasattr(adif, "USE_C_EXTENSIONS"):
        if adif.USE_C_EXTENSIONS:
            print("\n✅ C extensions are ENABLED")
        else:
            print("\n⚠️  C extensions are NOT available (using pure Python)")
    else:
        print("\n⚠️  Cannot determine C extension status")

    # Generate test data
    print("\n" + "="*60)
    print("Generating test data...")
    print("="*60)

    sizes = [1000, 10000, 50000]

    for size in sizes:
        print(f"\n\n{'#'*60}")
        print(f"TESTING WITH {size:,} QSOs")
        print(f"{'#'*60}")

        qsos = generate_test_data(size)
        adif_text = generate_adif_text(qsos)

        # Run benchmarks
        iterations = max(1, 100 // (size // 1000))  # Fewer iterations for large datasets

        parse_time = benchmark_adif_parsing(adif_text, iterations)
        awards_time = benchmark_awards_computation(qsos, iterations)
        export_time = benchmark_adif_export(qsos, iterations)

        # Summary
        print(f"\n{'='*60}")
        print(f"SUMMARY FOR {size:,} QSOs")
        print(f"{'='*60}")
        print(f"  ADIF parsing:      {parse_time:.3f}s ({size/parse_time:,.0f} QSOs/sec)")
        print(f"  Awards computation: {awards_time:.3f}s ({size/awards_time:,.0f} QSOs/sec)")
        print(f"  ADIF export:       {export_time:.3f}s ({size/export_time:,.0f} QSOs/sec)")

    print("\n" + "="*60)
    print("Benchmark complete!")
    print("="*60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Example: Using hyperthreading optimizations for W4GNS Logger.

This script demonstrates how to use the parallel_utils module to optimize
parallel processing based on CPU architecture and hyperthreading.
"""

from datetime import datetime
from pathlib import Path

from w4gns_logger_ai.models import QSO
from w4gns_logger_ai.parallel_utils import (
    get_cpu_info,
    get_optimal_batch_size,
    get_optimal_workers,
    should_use_parallel,
)


def example_optimized_adif_import():
    """Example: Optimize ADIF import with hyperthreading awareness."""
    
    # Get optimal worker count for I/O bound ADIF parsing
    optimal_workers = get_optimal_workers(workload_type="io")
    
    print("📂 ADIF Import Configuration:")
    print("  - Workload: I/O bound (file parsing)")
    print(f"  - Optimal workers: {optimal_workers}")
    
    # Example usage
    from w4gns_logger_ai.adif import load_adif_parallel
    
    adif_file = Path("large_logbook.adi")
    if adif_file.exists():
        text = adif_file.read_text()
        
        # Use optimized worker count
        qsos = load_adif_parallel(text, max_workers=optimal_workers)
        print(f"  - Imported {len(qsos)} QSOs")


def example_optimized_awards_compute():
    """Example: Optimize awards computation with CPU-aware workers."""
    
    # Get optimal worker count for CPU bound computation
    optimal_workers = get_optimal_workers(workload_type="cpu")
    
    print("\n🏆 Awards Computation Configuration:")
    print("  - Workload: CPU bound (calculations)")
    print(f"  - Optimal workers: {optimal_workers}")
    
    # Example with mock data
    qsos = [
        QSO(
            call=f"W{i}ABC",
            start_at=datetime(2024, 1, 1),
            band=["20m", "40m", "80m"][i % 3],
            mode=["SSB", "CW", "FT8"][i % 3],
        )
        for i in range(50000)
    ]
    
    # Check if parallel processing is worth it
    if should_use_parallel(len(qsos), threshold=10000):
        print(f"  - Using parallel processing ({len(qsos)} QSOs)")
        
        # Calculate optimal batch size
        batch_size = get_optimal_batch_size(
            total_items=len(qsos),
            num_workers=optimal_workers,
            min_batch=1000,
            max_batch=10000,
        )
        print(f"  - Batch size: {batch_size}")
        
        from w4gns_logger_ai.awards import compute_summary_parallel
        
        summary = compute_summary_parallel(qsos, chunk_size=batch_size)
        print(f"  - Processed: {summary['total_qsos']} QSOs")
        print(f"  - Unique countries: {summary['unique_countries']}")
    else:
        print(f"  - Using sequential processing ({len(qsos)} QSOs)")


def example_optimized_ai_calls():
    """Example: Optimize AI API calls with mixed workload awareness."""
    
    # Get optimal worker count for mixed I/O + CPU workload
    optimal_workers = get_optimal_workers(workload_type="mixed", max_workers=5)
    
    print("\n🤖 AI Processing Configuration:")
    print("  - Workload: Mixed (API calls + processing)")
    print(f"  - Optimal workers: {optimal_workers}")
    
    # Example with batches
    qso_batches = [
        [QSO(call=f"W{j}ABC", start_at=datetime(2024, 1, 1)) for j in range(i*10, (i+1)*10)]
        for i in range(10)
    ]
    
    print(f"  - Processing {len(qso_batches)} batches")
    
    # Note: In actual use, this would call the AI API
    # from w4gns_logger_ai.ai_helper import summarize_qsos_parallel
    # summaries = summarize_qsos_parallel(qso_batches, model="gpt-4o-mini")


def example_dynamic_optimization():
    """Example: Dynamically adjust parallelization based on dataset size."""
    
    print("\n⚙️  Dynamic Optimization:")
    
    # Simulate different dataset sizes
    for size in [100, 1000, 10000, 100000]:
        workers = get_optimal_workers("cpu")
        batch_size = get_optimal_batch_size(size, workers)
        use_parallel = should_use_parallel(size, threshold=1000)
        
        print(f"\n  Dataset: {size:,} items")
        print(f"    - Workers: {workers}")
        print(f"    - Batch size: {batch_size:,}")
        print(f"    - Use parallel: {'Yes ✓' if use_parallel else 'No ✗'}")
        
        if use_parallel:
            num_batches = (size + batch_size - 1) // batch_size
            print(f"    - Batches: {num_batches}")


def print_system_info():
    """Print comprehensive system and CPU information."""
    
    print("=" * 60)
    print("W4GNS Logger - Hyperthreading Optimization Info")
    print("=" * 60)
    
    info = get_cpu_info()
    
    print("\n💻 CPU Information:")
    if info.get("physical_cores"):
        print(f"  - Physical cores: {info['physical_cores']}")
        print(f"  - Logical cores: {info['logical_cores']}")
        
        if info.get("hyperthreading") is True:
            ht_factor = info['logical_cores'] / info['physical_cores']
            print(f"  - Hyperthreading: ✓ Enabled ({ht_factor:.1f}x)")
        elif info.get("hyperthreading") is False:
            print("  - Hyperthreading: ✗ Disabled")
        else:
            print("  - Hyperthreading: ? Unknown")
    
    if info.get("cpu_percent") is not None:
        print(f"  - CPU usage: {info['cpu_percent']:.1f}%")
    if info.get("memory_percent") is not None:
        print(f"  - Memory usage: {info['memory_percent']:.1f}%")
    
    print(f"  - CI environment: {'Yes' if info['is_ci'] else 'No'}")
    print(f"  - psutil available: {'Yes' if info['has_psutil'] else 'No'}")
    
    print("\n🎯 Optimal Worker Counts:")
    print(f"  - I/O bound (ADIF, exports): {info['optimal_workers']['io_bound']} workers")
    print(f"  - CPU bound (awards, stats): {info['optimal_workers']['cpu_bound']} workers")
    print(f"  - Mixed (AI, hybrid): {info['optimal_workers']['mixed']} workers")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Print system information
    print_system_info()
    
    # Run examples
    print("\n📋 Examples:\n")
    
    try:
        example_optimized_adif_import()
    except Exception as e:
        print(f"  ⚠ ADIF example skipped: {e}")
    
    example_optimized_awards_compute()
    example_optimized_ai_calls()
    example_dynamic_optimization()
    
    print("\n✅ Examples complete!\n")

#!/usr/bin/env python3
"""Hyperthreading optimization utilities.

This module provides enhanced parallel processing with optimized worker counts
based on physical vs logical CPU cores for better hyperthreading utilization.
"""

import multiprocessing
import os
from typing import Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def get_optimal_workers(
    workload_type: str = "io",
    max_workers: Optional[int] = None,
) -> int:
    """Calculate optimal worker count based on workload type and hyperthreading.
    
    Args:
        workload_type: Type of workload
            - "io": I/O bound (file, network, API) - benefits from hyperthreading
            - "cpu": CPU bound (computation) - doesn't benefit from hyperthreading  
            - "mixed": Mixed I/O and CPU - moderate hyperthreading benefit
        max_workers: Optional maximum to cap the result
    
    Returns:
        Optimal number of workers for the workload type
    
    Examples:
        >>> # For ADIF parsing (I/O bound)
        >>> workers = get_optimal_workers("io")
        
        >>> # For awards computation (CPU bound)
        >>> workers = get_optimal_workers("cpu")
        
        >>> # For AI calls (mixed)
        >>> workers = get_optimal_workers("mixed")
    """
    # Detect CI environment - use conservative settings
    is_ci = any(env in os.environ for env in ['CI', 'GITHUB_ACTIONS', 'TRAVIS', 'JENKINS'])
    
    if is_ci:
        # CI environments: use minimal workers to avoid resource contention
        base_workers = 2
    else:
        # Get physical and logical core counts
        if HAS_PSUTIL:
            physical_cores = psutil.cpu_count(logical=False) or 1
            logical_cores = psutil.cpu_count(logical=True) or physical_cores
        else:
            # Fallback to multiprocessing
            logical_cores = multiprocessing.cpu_count() or 1
            # Estimate physical cores (rough heuristic)
            physical_cores = max(1, logical_cores // 2)
        
        # Calculate workers based on workload type
        if workload_type == "io":
            # I/O bound: Use 2x physical cores (benefits from hyperthreading)
            base_workers = min(physical_cores * 2, logical_cores)
        elif workload_type == "cpu":
            # CPU bound: Use physical cores only (no hyperthreading benefit)
            base_workers = physical_cores
        elif workload_type == "mixed":
            # Mixed: Use 1.5x physical cores (moderate hyperthreading benefit)
            base_workers = int(physical_cores * 1.5)
        else:
            # Unknown: Conservative default
            base_workers = logical_cores
    
    # Apply maximum limit if specified
    if max_workers is not None:
        base_workers = min(base_workers, max_workers)
    
    # Ensure at least 1 worker
    return max(1, base_workers)


def get_optimal_batch_size(
    total_items: int,
    num_workers: int,
    min_batch: int = 100,
    max_batch: int = 10000,
) -> int:
    """Calculate optimal batch size for parallel processing.
    
    Args:
        total_items: Total number of items to process
        num_workers: Number of parallel workers
        min_batch: Minimum batch size
        max_batch: Maximum batch size
    
    Returns:
        Optimal batch size for load balancing
    
    Examples:
        >>> workers = get_optimal_workers("cpu")
        >>> batch_size = get_optimal_batch_size(100000, workers)
    """
    if total_items < min_batch:
        return total_items
    
    # Aim for 2-4 batches per worker for good load balancing
    target_batches = num_workers * 3
    ideal_batch = max(min_batch, total_items // target_batches)
    
    return min(max_batch, ideal_batch)


def should_use_parallel(
    item_count: int,
    threshold: int = 100,
    force_parallel: Optional[bool] = None,
) -> bool:
    """Determine if parallel processing should be used.
    
    Args:
        item_count: Number of items to process
        threshold: Minimum items for parallel processing
        force_parallel: Override automatic decision
    
    Returns:
        True if parallel processing should be used
    """
    if force_parallel is not None:
        return force_parallel
    
    # CI environments: higher threshold to avoid overhead
    is_ci = any(env in os.environ for env in ['CI', 'GITHUB_ACTIONS', 'TRAVIS', 'JENKINS'])
    
    if is_ci:
        threshold = max(threshold, 500)
    
    return item_count >= threshold


def get_cpu_info() -> dict:
    """Get CPU information for debugging and optimization.
    
    Returns:
        Dictionary with CPU details
    """
    info = {
        "has_psutil": HAS_PSUTIL,
        "is_ci": any(env in os.environ for env in ['CI', 'GITHUB_ACTIONS', 'TRAVIS', 'JENKINS']),
    }
    
    if HAS_PSUTIL:
        info.update({
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "hyperthreading": psutil.cpu_count(logical=True) > psutil.cpu_count(logical=False),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
        })
    else:
        logical_cores = multiprocessing.cpu_count() or 1
        info.update({
            "physical_cores": max(1, logical_cores // 2),  # Estimate
            "logical_cores": logical_cores,
            "hyperthreading": None,  # Unknown
        })
    
    # Calculate optimal workers for different workloads
    info["optimal_workers"] = {
        "io_bound": get_optimal_workers("io"),
        "cpu_bound": get_optimal_workers("cpu"),
        "mixed": get_optimal_workers("mixed"),
    }
    
    return info


if __name__ == "__main__":
    """Print CPU info and optimal worker counts."""
    import json
    
    info = get_cpu_info()
    print(json.dumps(info, indent=2))
    
    print("\nRecommendations:")
    print(f"  - ADIF parsing (I/O): {info['optimal_workers']['io_bound']} workers")
    print(f"  - Awards compute (CPU): {info['optimal_workers']['cpu_bound']} workers")
    print(f"  - AI calls (Mixed): {info['optimal_workers']['mixed']} workers")
    
    if info.get("hyperthreading"):
        print(
            f"\n✓ Hyperthreading detected: {info['logical_cores']} logical"
            f" / {info['physical_cores']} physical cores"
        )
    else:
        print("\n⚠ Hyperthreading status unknown")

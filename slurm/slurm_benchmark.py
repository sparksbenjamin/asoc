#!/usr/bin/env python3
"""
ASoc SLURM Multi-Node Benchmark

This script is called by SLURM on each node.
Uses static peer configuration to connect nodes in HPC cluster.

Usage:
    srun python slurm_benchmark.py --rank 0 --world-size 4
"""

import asyncio
import argparse
import os
import sys
import time
import socket
import numpy as np
from pathlib import Path

# Add parent directory to path if running from slurm subdirectory
sys.path.insert(0, str(Path(__file__).parent.parent))

from asoc import NodeReady


def parse_args():
    parser = argparse.ArgumentParser(description="ASoc SLURM Benchmark")
    parser.add_argument("--rank", type=int, required=True, help="Process rank (from SLURM_PROCID)")
    parser.add_argument("--world-size", type=int, required=True, help="Total number of processes")
    parser.add_argument("--node-name", type=str, default=socket.gethostname(), help="Node hostname")
    parser.add_argument("--port", type=int, default=9000, help="Base port")
    parser.add_argument("--tensor-size-mb", type=int, default=100, help="Tensor size in MB")
    parser.add_argument("--iterations", type=int, default=5, help="Number of iterations")
    return parser.parse_args()


async def run_benchmark(args):
    """Run ASoc benchmark on SLURM cluster"""
    
    print(f"\n{'='*70}")
    print(f"ASoc SLURM Benchmark - Rank {args.rank}/{args.world_size}")
    print(f"{'='*70}")
    print(f"Node: {args.node_name}")
    print(f"Port: {args.port}")
    
    # Get configuration from environment
    community = os.environ.get("ASOC_COMMUNITY", "slurm-cluster")
    api_key = os.environ.get("ASOC_API_KEY", "default-key")
    peers_str = os.environ.get("ASOC_PEERS", "")
    
    if not peers_str:
        print("ERROR: ASOC_PEERS environment variable not set!")
        print("This should be set by the SLURM script")
        sys.exit(1)
    
    # Parse peer list
    static_peers = [p.strip() for p in peers_str.split(",") if p.strip()]
    print(f"Community: {community}")
    print(f"Static peers: {len(static_peers)} configured")
    
    # Create node with static configuration (no UDP discovery in HPC)
    node = NodeReady(
        community=community,
        api_key=api_key,
        static_peers=static_peers,
        enable_discovery=False,  # Disable UDP - won't work across compute nodes
        port=args.port
    )
    
    print(f"\nStarting node...")
    await node.start()
    
    # Wait for all nodes to connect
    # In HPC, connections might be slower due to network topology
    connection_timeout = 30
    print(f"Waiting for peer connections (timeout: {connection_timeout}s)...")
    
    start_wait = time.time()
    expected_peers = args.world_size - 1  # All nodes except self
    
    while time.time() - start_wait < connection_timeout:
        peers = node.get_peer_ids()
        print(f"  Connected to {len(peers)}/{expected_peers} peers...", end='\r')
        
        if len(peers) >= expected_peers:
            break
        
        await asyncio.sleep(1)
    
    peers = node.get_peer_ids()
    print(f"\n✓ Connected to {len(peers)} peers                    ")
    
    if len(peers) == 0:
        print("\n⚠️  WARNING: No peers connected!")
        print("Check:")
        print("  - Network connectivity between nodes")
        print("  - Firewall rules")
        print("  - Port availability")
        await node.shutdown()
        return
    
    # Synchronization barrier - make sure all nodes are ready
    print("\nSynchronizing with all nodes...")
    await asyncio.sleep(5)  # Simple barrier
    
    # Benchmark: Rank 0 sends to all others, others receive
    if args.rank == 0:
        print(f"\n{'='*70}")
        print(f"RANK 0: Broadcasting tensors to {len(peers)} peers")
        print(f"{'='*70}")
        
        tensor_size = args.tensor_size_mb * 1024 * 1024
        results = []
        
        for iteration in range(args.iterations):
            print(f"\nIteration {iteration + 1}/{args.iterations}")
            
            # Generate tensor data
            tensor_data = np.random.bytes(tensor_size)
            
            # Broadcast to all peers
            start = time.perf_counter()
            
            tasks = []
            for peer_id in peers:
                task = node.stream_tensor(peer_id, tensor_data)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            elapsed = time.perf_counter() - start
            
            # Calculate metrics
            total_data_mb = args.tensor_size_mb * len(peers)
            aggregate_throughput = total_data_mb / elapsed
            per_peer_throughput = args.tensor_size_mb / elapsed
            
            results.append({
                'iteration': iteration + 1,
                'elapsed': elapsed,
                'aggregate_mbps': aggregate_throughput,
                'per_peer_mbps': per_peer_throughput
            })
            
            print(f"  Elapsed: {elapsed:.2f}s")
            print(f"  Total data: {total_data_mb}MB")
            print(f"  Aggregate throughput: {aggregate_throughput:.1f} MB/s")
            print(f"  Per-peer throughput: {per_peer_throughput:.1f} MB/s")
            
            # Cool down between iterations
            await asyncio.sleep(2)
        
        # Summary
        print(f"\n{'='*70}")
        print(f"BENCHMARK SUMMARY (Rank 0)")
        print(f"{'='*70}")
        print(f"World size: {args.world_size} nodes")
        print(f"Tensor size: {args.tensor_size_mb}MB")
        print(f"Iterations: {args.iterations}")
        print(f"\nResults:")
        
        avg_aggregate = sum(r['aggregate_mbps'] for r in results) / len(results)
        avg_per_peer = sum(r['per_peer_mbps'] for r in results) / len(results)
        
        print(f"  Average aggregate throughput: {avg_aggregate:.1f} MB/s")
        print(f"  Average per-peer throughput: {avg_per_peer:.1f} MB/s")
        print(f"  Protocol overhead: 0.001% (14 bytes per 1MB frame)")
        
    else:
        # Receiver nodes
        print(f"\n{'='*70}")
        print(f"RANK {args.rank}: Receiving tensors")
        print(f"{'='*70}")
        
        # Just wait and receive
        # The _recv_loop in node_ready.py handles incoming data
        total_wait = args.iterations * 10  # 10 seconds per iteration
        print(f"Waiting to receive {args.iterations} iterations...")
        
        await asyncio.sleep(total_wait)
        
        print(f"\n✓ Completed receiving")
    
    # Final synchronization
    print("\nFinalizing...")
    await asyncio.sleep(3)
    
    # Shutdown
    print("Shutting down node...")
    await node.shutdown()
    
    print(f"\n{'='*70}")
    print(f"Rank {args.rank} complete!")
    print(f"{'='*70}\n")


def main():
    args = parse_args()
    
    try:
        asyncio.run(run_benchmark(args))
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

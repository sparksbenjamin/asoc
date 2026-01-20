"""
Working ASoc Benchmark

Tests throughput and latency with the production-ready node
"""

import asyncio
import time
import statistics
import sys

# Import numpy if available, otherwise use random
try:
    import numpy as np
    def generate_data(size_bytes):
        return np.random.bytes(size_bytes)
except ImportError:
    import random
    def generate_data(size_bytes):
        return bytes(random.getrandbits(8) for _ in range(size_bytes))

from asoc import NodeReady


async def benchmark_throughput():
    """Benchmark raw throughput"""
    
    print("=" * 70)
    print("ASoc Throughput Benchmark")
    print("=" * 70)
    
    # Create nodes
    sender = NodeReady(
        community="bench",
        api_key="benchmark-key",
        port=9001
    )
    
    receiver = NodeReady(
        community="bench",
        api_key="benchmark-key",
        port=9002
    )
    
    print("\n📡 Starting nodes...")
    await sender.start()
    await receiver.start()
    
    print("⏳ Waiting for connection...")
    await asyncio.sleep(4)
    
    peers = sender.get_peer_ids()
    if not peers:
        print("❌ ERROR: Nodes failed to connect!")
        print("   Check firewall or try static configuration")
        await sender.shutdown()
        await receiver.shutdown()
        return
    
    peer_id = peers[0]
    print(f"✅ Connected to {peer_id[:8]}\n")
    
    # Test different sizes
    sizes_mb = [1, 10, 50, 100]
    results = []
    
    print(f"{'Size':<10} {'Time':<10} {'Throughput':<15} {'Overhead':<10}")
    print("-" * 70)
    
    for size_mb in sizes_mb:
        size_bytes = size_mb * 1024 * 1024
        data = generate_data(size_bytes)
        
        # Warm up
        if size_mb == sizes_mb[0]:
            await sender.stream_tensor(peer_id, data[:1024*1024])
            await asyncio.sleep(0.5)
        
        # Benchmark
        start = time.perf_counter()
        await sender.stream_tensor(peer_id, data)
        
        # Small delay to let receiver finish processing
        await asyncio.sleep(0.2)
        
        elapsed = time.perf_counter() - start
        throughput_mbps = size_mb / elapsed
        
        # Calculate overhead
        header_bytes = 14  # Per frame
        num_frames = (size_bytes + 1024*1024 - 1) // (1024*1024)  # Ceiling division
        total_overhead = header_bytes * num_frames
        overhead_pct = (total_overhead / size_bytes) * 100
        
        results.append({
            'size_mb': size_mb,
            'time': elapsed,
            'throughput': throughput_mbps
        })
        
        print(f"{size_mb:3d} MB    {elapsed:6.2f}s    "
              f"{throughput_mbps:8.1f} MB/s    {overhead_pct:.3f}%")
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary:")
    throughputs = [r['throughput'] for r in results]
    print(f"  Average throughput: {statistics.mean(throughputs):.1f} MB/s")
    print(f"  Peak throughput: {max(throughputs):.1f} MB/s")
    print(f"  Protocol overhead: < 0.002% (14 bytes per 1MB frame)")
    print("=" * 70)
    
    await sender.shutdown()
    await receiver.shutdown()


async def benchmark_latency():
    """Benchmark latency for small messages"""
    
    print("\n" + "=" * 70)
    print("ASoc Latency Benchmark (Small Messages)")
    print("=" * 70)
    
    sender = NodeReady(
        community="latency-bench",
        api_key="bench-key",
        port=9003
    )
    
    receiver = NodeReady(
        community="latency-bench",
        api_key="bench-key",
        port=9004
    )
    
    await sender.start()
    await receiver.start()
    await asyncio.sleep(4)
    
    peers = sender.get_peer_ids()
    if not peers:
        print("❌ Nodes failed to connect")
        await sender.shutdown()
        await receiver.shutdown()
        return
    
    peer_id = peers[0]
    print(f"✅ Connected\n")
    
    # Test different message sizes
    sizes = [
        (1, "KB"),
        (10, "KB"),
        (100, "KB"),
        (1, "MB")
    ]
    
    iterations = 20
    
    print(f"{'Size':<12} {'Iterations':<12} {'Mean':<12} {'Median':<12} {'P99':<12}")
    print("-" * 70)
    
    for size_val, size_unit in sizes:
        if size_unit == "KB":
            size_bytes = size_val * 1024
        else:
            size_bytes = size_val * 1024 * 1024
        
        data = generate_data(size_bytes)
        latencies = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            await sender.stream_tensor(peer_id, data)
            elapsed = time.perf_counter() - start
            latencies.append(elapsed * 1000)  # Convert to ms
            
            await asyncio.sleep(0.01)  # Brief pause
        
        mean_lat = statistics.mean(latencies)
        median_lat = statistics.median(latencies)
        p99_lat = sorted(latencies)[int(0.99 * len(latencies))]
        
        print(f"{size_val:3d} {size_unit:<8} {iterations:<12} "
              f"{mean_lat:8.2f}ms   {median_lat:8.2f}ms   {p99_lat:8.2f}ms")
    
    print("=" * 70)
    
    await sender.shutdown()
    await receiver.shutdown()


async def benchmark_concurrent():
    """Benchmark concurrent streams"""
    
    print("\n" + "=" * 70)
    print("ASoc Concurrent Streams Benchmark")
    print("=" * 70)
    
    sender = NodeReady(
        community="concurrent-bench",
        api_key="bench-key",
        port=9005
    )
    
    receiver = NodeReady(
        community="concurrent-bench",
        api_key="bench-key",
        port=9006
    )
    
    await sender.start()
    await receiver.start()
    await asyncio.sleep(4)
    
    peers = sender.get_peer_ids()
    if not peers:
        print("❌ Nodes failed to connect")
        await sender.shutdown()
        await receiver.shutdown()
        return
    
    peer_id = peers[0]
    print(f"✅ Connected\n")
    
    # Test with different numbers of concurrent streams
    stream_counts = [1, 5, 10, 20]
    tensor_size_mb = 5
    
    print(f"{'Streams':<12} {'Total Data':<15} {'Time':<12} {'Throughput':<15}")
    print("-" * 70)
    
    for num_streams in stream_counts:
        data = generate_data(tensor_size_mb * 1024 * 1024)
        
        start = time.perf_counter()
        
        # Send multiple streams concurrently
        tasks = [
            sender.stream_tensor(peer_id, data)
            for _ in range(num_streams)
        ]
        
        await asyncio.gather(*tasks)
        
        elapsed = time.perf_counter() - start
        total_mb = tensor_size_mb * num_streams
        throughput = total_mb / elapsed
        
        print(f"{num_streams:<12} {total_mb:3d} MB{'':<8} "
              f"{elapsed:8.2f}s   {throughput:8.1f} MB/s")
    
    print("=" * 70)
    
    await sender.shutdown()
    await receiver.shutdown()


async def main():
    """Run all benchmarks"""
    
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                   ASoc Protocol Benchmark Suite                    ║
║                                                                     ║
║  Testing:                                                           ║
║  • Throughput (1MB - 100MB)                                        ║
║  • Latency (small messages)                                        ║
║  • Concurrent streams                                              ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        await benchmark_throughput()
        await asyncio.sleep(2)
        
        await benchmark_latency()
        await asyncio.sleep(2)
        
        await benchmark_concurrent()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted")
    except Exception as e:
        print(f"\n\n❌ Benchmark error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Benchmark complete!\n")


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ required")
        sys.exit(1)
    
    asyncio.run(main())

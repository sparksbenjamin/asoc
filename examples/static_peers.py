"""
Static Configuration Example

Use this when UDP discovery doesn't work:
- Firewalls blocking UDP port 9999
- VLANs separating nodes
- Cloud deployments
- Kubernetes clusters
"""

import asyncio
from asoc import NodeReady


async def main():
    print("=" * 60)
    print("ASoc Static Configuration Example")
    print("=" * 60)
    
    print("\nThis example shows how to configure peers manually")
    print("instead of using UDP auto-discovery.\n")
    
    # Node A: Configured to connect to Node B at localhost:9002
    print("1. Creating Node A (will connect to localhost:9002)...")
    node_a = NodeReady(
        community="static-cluster",
        api_key="static-key",
        static_peers=["127.0.0.1:9002"],  # Connect to Node B
        enable_discovery=False,  # Disable UDP discovery
        port=9001
    )
    
    # Node B: Configured to connect to Node A at localhost:9001
    print("2. Creating Node B (will connect to localhost:9001)...")
    node_b = NodeReady(
        community="static-cluster",
        api_key="static-key",
        static_peers=["127.0.0.1:9001"],  # Connect to Node A
        enable_discovery=False,  # Disable UDP discovery
        port=9002
    )
    
    # Start both nodes
    print("\n3. Starting nodes...")
    await node_a.start()
    await node_b.start()
    
    # Wait for connection (static peers connect more slowly)
    print("4. Waiting for peer connection (5 seconds)...")
    await asyncio.sleep(5)
    
    # Check connection
    peers_a = node_a.get_peer_ids()
    
    print(f"\nNode A peers: {len(peers_a)}")
    
    if peers_a:
        print("\n5. Sending data...")
        data = b"Static configuration works!" * 100
        await node_a.stream_tensor(peers_a[0], data)
        print("✓ Data sent successfully!")
        
        await asyncio.sleep(1)
    else:
        print("\n⚠️  Nodes didn't connect. Check:")
        print("   - Both nodes are running")
        print("   - Ports 9001, 9002 are not blocked")
        print("   - API keys match")
    
    # Cleanup
    print("\n6. Shutting down...")
    await node_a.shutdown()
    await node_b.shutdown()
    
    print("\n" + "=" * 60)
    print("Example complete!")
    print("\nFor production deployment with environment variables:")
    print("  export ASOC_PEERS='10.0.1.10:9000,10.0.2.20:9000'")
    print("  python your_script.py")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

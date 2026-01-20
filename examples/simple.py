"""
Simple ASoc Example - Two Nodes Communicating

This example shows the minimal code needed to:
1. Create two nodes
2. Let them discover each other
3. Stream tensor data between them
"""

import asyncio
from asoc import NodeReady


async def main():
    print("=" * 60)
    print("ASoc Simple Example")
    print("=" * 60)
    
    # Create two nodes on different ports
    print("\n1. Creating nodes...")
    node_a = NodeReady(
        community="example-cluster",
        api_key="example-key",
        port=9001
    )
    
    node_b = NodeReady(
        community="example-cluster",
        api_key="example-key",
        port=9002
    )
    
    # Start both nodes
    print("2. Starting nodes...")
    await node_a.start()
    await node_b.start()
    
    # Wait for discovery
    print("3. Waiting for peer discovery (3 seconds)...")
    await asyncio.sleep(3)
    
    # Check if nodes found each other
    peers_a = node_a.get_peer_ids()
    peers_b = node_b.get_peer_ids()
    
    print(f"\nNode A found {len(peers_a)} peer(s)")
    print(f"Node B found {len(peers_b)} peer(s)")
    
    if peers_a:
        print(f"\n4. Streaming tensor from Node A to Node B...")
        
        # Create some example data (in real use, this would be your tensor)
        tensor_data = b"Example tensor data " * 1000  # ~20KB
        
        # Stream it to the peer
        await node_a.stream_tensor(peers_a[0], tensor_data)
        
        print("✓ Tensor streamed successfully!")
        
        # Give receiver time to process
        await asyncio.sleep(1)
    else:
        print("\n⚠️  No peers discovered. Check firewall settings.")
        print("   Try static configuration instead (see README.md)")
    
    # Clean shutdown
    print("\n5. Shutting down...")
    await node_a.shutdown()
    await node_b.shutdown()
    
    print("\n" + "=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

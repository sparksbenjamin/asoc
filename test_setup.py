#!/usr/bin/env python3
"""
Quick test to verify ASoc setup works

Run this first to make sure everything is working before benchmarking
"""

import asyncio
import sys

# Check Python version
if sys.version_info < (3, 7):
    print("❌ Error: Python 3.7+ required")
    print(f"   You have: {sys.version}")
    sys.exit(1)

print("✓ Python version OK")

# Try imports
try:
    from asoc import NodeReady
    print("✓ asoc.NodeReady imported")
except ImportError as e:
    print(f"❌ Error importing asoc: {e}")
    print("   Make sure asoc/ directory is present with all files")
    sys.exit(1)

try:
    from asoc import encode_frame, decode_header
    print("✓ asoc.protocol imported")
except ImportError as e:
    print(f"❌ Error importing asoc protocol: {e}")
    sys.exit(1)

try:
    from asoc import BinaryDiscovery
    print("✓ asoc.discovery imported")
except ImportError as e:
    print(f"❌ Error importing asoc discovery: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("Quick Connection Test")
print("="*60)


async def test_connection():
    """Test basic node connection"""
    
    print("\n1. Creating nodes...")
    node1 = NodeReady(
        community="test",
        api_key="test-key",
        port=9001
    )
    
    node2 = NodeReady(
        community="test",
        api_key="test-key",
        port=9002
    )
    
    print("✓ Nodes created")
    
    print("\n2. Starting nodes...")
    await node1.start()
    await node2.start()
    print("✓ Nodes started")
    
    print("\n3. Waiting for discovery (5 seconds)...")
    for i in range(5, 0, -1):
        print(f"   {i}...", end='\r')
        await asyncio.sleep(1)
    print("   Done!   ")
    
    print("\n4. Checking connection...")
    peers1 = node1.get_peer_ids()
    peers2 = node2.get_peer_ids()
    
    if peers1:
        print(f"✓ Node 1 connected to: {peers1[0][:8]}...")
    else:
        print("⚠️  Node 1 has no peers")
    
    if peers2:
        print(f"✓ Node 2 connected to: {peers2[0][:8]}...")
    else:
        print("⚠️  Node 2 has no peers")
    
    if peers1 and peers2:
        print("\n5. Testing data transfer...")
        test_data = b"Hello, ASoc!" * 100
        
        try:
            await node1.stream_tensor(peers1[0], test_data)
            print("✓ Data sent successfully")
            
            # Small delay for receiver
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Error sending data: {e}")
    else:
        print("\n⚠️  Skipping data transfer (no connection)")
        print("\nPossible issues:")
        print("  - Firewall blocking UDP port 9999")
        print("  - Running on different subnets")
        print("  - Try static configuration instead")
    
    print("\n6. Shutting down...")
    await node1.shutdown()
    await node2.shutdown()
    print("✓ Clean shutdown")
    
    print("\n" + "="*60)
    if peers1 and peers2:
        print("✅ ALL TESTS PASSED - Ready for benchmarking!")
    else:
        print("⚠️  TESTS COMPLETED WITH WARNINGS")
        print("\nTo use static configuration instead of discovery:")
        print('  node = NodeReady(')
        print('      community="test",')
        print('      api_key="test-key",')
        print('      static_peers=["127.0.0.1:9002"],')
        print('      enable_discovery=False')
        print('  )')
    print("="*60)


async def main():
    try:
        await test_connection()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("\nASoc Quick Test")
    print("This will verify your setup is working\n")
    asyncio.run(main())

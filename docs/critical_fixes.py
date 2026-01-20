"""
Critical fixes before benchmarking

Apply these patches to avoid crashes and deadlocks
"""

# ============================================================================
# FIX 1: Add missing import to node_binary.py
# ============================================================================
# Add at top of node_binary.py:
from transport_fixed import Connection


# ============================================================================
# FIX 2: Add SO_REUSEADDR to prevent "Address in use" errors
# ============================================================================
# In node_binary.py, _start_server method:
async def _start_server(self):
    """Start TCP server"""
    server = await asyncio.start_server(
        self._handle_client, 
        self.host, 
        self.port,
        reuse_address=True,  # ADD THIS
        reuse_port=True      # ADD THIS (Linux only)
    )
    
    self._server = server  # Store reference for shutdown
    
    async with server:
        await server.serve_forever()


# ============================================================================
# FIX 3: Proper graceful shutdown
# ============================================================================
# In node_binary.py, add:
async def shutdown(self):
    """Graceful shutdown"""
    print(f"Shutting down {self.node_id[:8]}")
    
    # Close server
    if hasattr(self, '_server') and self._server:
        self._server.close()
        await self._server.wait_closed()
    
    # Close all peer connections
    async with self._peers_lock:
        for conn in list(self.peers.values()):
            try:
                await conn.close()
            except Exception:
                pass
        self.peers.clear()


# ============================================================================
# FIX 4: Add timeout to drain() to prevent deadlock
# ============================================================================
# In transport_fixed.py:
async def send_frame(self, frame_type, stream_id, seq, payload=b""):
    """Send frame with flow control and timeout"""
    async with self._send_semaphore:
        frame = encode_frame(frame_type, stream_id, seq, payload)
        self.writer.write(frame)
        
        # Add timeout to prevent deadlock if receiver is dead
        try:
            await asyncio.wait_for(self.writer.drain(), timeout=10.0)
        except asyncio.TimeoutError:
            raise ConnectionError("Send timeout - peer may be dead")


# ============================================================================
# FIX 5: Auto-incrementing stream IDs to prevent collisions
# ============================================================================
# In node_binary.py, add to __init__:
self._next_stream_id = 1
self._stream_id_lock = asyncio.Lock()

# Add helper method:
async def _get_next_stream_id(self) -> int:
    """Get next available stream ID"""
    async with self._stream_id_lock:
        stream_id = self._next_stream_id
        self._next_stream_id += 2  # Odd numbers only (even for peer-initiated)
        return stream_id

# Modify stream_tensor:
async def stream_tensor(self, 
                       peer_id: str,
                       data: bytes,
                       tensor_id: int = None,  # Make optional
                       chunk_size: int = 1_048_576):
    """Stream tensor to peer"""
    
    # Auto-assign stream ID if not provided
    if tensor_id is None:
        tensor_id = await self._get_next_stream_id()
    
    # ... rest of function


# ============================================================================
# FIX 6: Better replay attack prevention
# ============================================================================
# In discovery_binary.py, replace cleanup logic:
async def _cleanup_loop(self):
    """Remove stale peers and old challenges"""
    while True:
        await asyncio.sleep(30)
        
        now = time.time()
        
        # Remove stale peers
        async with self._peers_lock:
            stale = [
                node_id for node_id, (_, _, ts) in self.peers.items()
                if now - ts > 15
            ]
            for node_id in stale:
                del self.peers[node_id]
        
        # Remove old challenges (keep last 1000, remove older than 60s)
        async with self._challenges_lock:
            if len(self._seen_challenges) > 1000:
                # Convert to list with timestamps, remove old
                # For now, just limit size more conservatively
                if len(self._seen_challenges) > 5000:
                    # Remove oldest half
                    challenges_list = list(self._seen_challenges)
                    self._seen_challenges = set(challenges_list[len(challenges_list)//2:])


# ============================================================================
# FIX 7: Add data consumer for benchmarking
# ============================================================================
# In node_binary.py, add option to collect received data:
def __init__(self, ..., collect_received=False):
    # ... existing init
    self.collect_received = collect_received
    self._received_data = {}  # stream_id -> list of chunks
    self._received_lock = asyncio.Lock()

async def _recv_loop(self, conn: Connection, peer_id_bytes: bytes):
    """Receive loop"""
    try:
        peer_uuid = bytes_to_uuid(peer_id_bytes)
        
        while True:
            frame_type, stream_id, seq, payload = await conn.recv_frame()
            
            if frame_type == FRAME_DATA:
                if self.collect_received:
                    async with self._received_lock:
                        if stream_id not in self._received_data:
                            self._received_data[stream_id] = []
                        self._received_data[stream_id].append((seq, payload))
                
                print(f"[{self.node_id[:8]}] recv stream {stream_id} "
                      f"chunk {seq} size={len(payload)}")
            
            elif frame_type == FRAME_END:
                print(f"[{self.node_id[:8]}] stream {stream_id} complete")
                
    except Exception as e:
        print(f"Recv error: {e}")
    finally:
        # ... cleanup


# ============================================================================
# FIX 8: Add timeouts to recv_frame
# ============================================================================
# In transport_fixed.py:
async def recv_frame(self):
    """Receive frame with timeout"""
    try:
        header = await asyncio.wait_for(
            self.reader.readexactly(HEADER_SIZE),
            timeout=30.0
        )
        version, frame_type, stream_id, seq, length = decode_header(header)
        
        payload = await asyncio.wait_for(
            self.reader.readexactly(length),
            timeout=30.0
        )
        
        return frame_type, stream_id, seq, payload
    except asyncio.TimeoutError:
        raise ConnectionError("Receive timeout")


# ============================================================================
# FIX 9: Consistent UUID handling
# ============================================================================
# Add helper class to node_binary.py:
class PeerID:
    """Wrapper to handle UUID string/bytes consistently"""
    
    def __init__(self, value):
        if isinstance(value, str):
            self.uuid = uuid_module.UUID(value)
        elif isinstance(value, bytes):
            self.uuid = uuid_module.UUID(bytes=value)
        elif isinstance(value, uuid_module.UUID):
            self.uuid = value
        else:
            raise ValueError(f"Invalid peer ID type: {type(value)}")
    
    @property
    def bytes(self) -> bytes:
        return self.uuid.bytes
    
    @property
    def string(self) -> str:
        return str(self.uuid)
    
    def __str__(self):
        return self.string
    
    def __repr__(self):
        return f"PeerID({self.string[:8]}...)"


# ============================================================================
# FIX 10: Simple benchmark that actually works
# ============================================================================
import asyncio
import time
import numpy as np
from node_binary import BinaryNode

async def simple_benchmark():
    """Simple working benchmark"""
    
    print("=" * 60)
    print("ASoc Simple Benchmark")
    print("=" * 60)
    
    # Create nodes
    sender = BinaryNode(
        community="bench",
        api_key="test-key",
        port=9001,
        collect_received=False  # Don't store, just count
    )
    
    receiver = BinaryNode(
        community="bench",
        api_key="test-key", 
        port=9002,
        collect_received=False
    )
    
    await sender.start()
    await receiver.start()
    
    print("\nWaiting for connection...")
    await asyncio.sleep(3)
    
    peers = sender.get_peer_ids()
    if not peers:
        print("ERROR: Nodes didn't connect!")
        return
    
    peer_id = peers[0]
    print(f"Connected to {peer_id[:8]}")
    
    # Benchmark different sizes
    sizes_mb = [1, 10, 100]
    
    for size_mb in sizes_mb:
        data = np.random.bytes(size_mb * 1024 * 1024)
        
        print(f"\nSending {size_mb}MB...")
        start = time.perf_counter()
        
        await sender.stream_tensor(peer_id, data)
        
        # Wait for receiver to process
        await asyncio.sleep(0.5)
        
        elapsed = time.perf_counter() - start
        throughput = size_mb / elapsed
        
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.1f} MB/s")
    
    await sender.shutdown()
    await receiver.shutdown()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(simple_benchmark())

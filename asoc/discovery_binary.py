import asyncio
import socket
import time
import secrets
from .protocol_binary import encode_discovery, decode_discovery, bytes_to_uuid

DISCOVERY_PORT = 9999
BROADCAST_ADDR = "<broadcast>"
DISCOVERY_INTERVAL = 3


class BinaryDiscovery:
    """
    Ultra-compact binary discovery
    
    Message size: 50 bytes (vs 150+ for JSON)
    - Community hash: 8 bytes
    - Node ID: 16 bytes  
    - Port: 2 bytes
    - Timestamp: 4 bytes
    - Challenge: 4 bytes
    - Signature: 16 bytes
    """
    
    def __init__(self, node_id_bytes: bytes, listen_port: int, 
                 community: str, api_key: bytes):
        self.node_id_bytes = node_id_bytes  # 16 bytes
        self.listen_port = listen_port
        self.community = community
        self.api_key = api_key
        
        # Discovered peers
        self.peers = {}  # node_id_bytes -> (ip, port, timestamp)
        self._peers_lock = asyncio.Lock()
        
        # Replay protection
        self._seen_challenges = set()
        self._challenges_lock = asyncio.Lock()
    
    async def start(self):
        asyncio.create_task(self._broadcast_loop())
        asyncio.create_task(self._listen_loop())
        asyncio.create_task(self._cleanup_loop())
    
    async def _broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setblocking(False)
        
        loop = asyncio.get_running_loop()
        
        while True:
            try:
                # Generate random challenge each time
                challenge = secrets.randbits(32)
                
                # Encode as 50-byte binary message
                msg = encode_discovery(
                    self.community,
                    self.node_id_bytes,
                    self.listen_port,
                    self.api_key,
                    timestamp=int(time.time()),
                    challenge=challenge
                )
                
                await loop.sock_sendto(sock, msg, (BROADCAST_ADDR, DISCOVERY_PORT))
            except Exception:
                pass
            
            await asyncio.sleep(DISCOVERY_INTERVAL)
    
    async def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", DISCOVERY_PORT))
        sock.setblocking(False)
        
        loop = asyncio.get_running_loop()
        
        while True:
            try:
                data, addr = await loop.sock_recvfrom(sock, 1024)
                
                # Decode and verify (returns None if invalid)
                parsed = decode_discovery(data, self.community, self.api_key)
                
                if not parsed:
                    continue
                
                # Ignore our own broadcasts
                if parsed['node_id'] == self.node_id_bytes:
                    continue
                
                # Check for replay attacks
                async with self._challenges_lock:
                    if parsed['challenge'] in self._seen_challenges:
                        continue
                    self._seen_challenges.add(parsed['challenge'])
                
                # Valid peer discovered
                async with self._peers_lock:
                    self.peers[parsed['node_id']] = (
                        addr[0], 
                        parsed['port'],
                        time.time()
                    )
                
                node_uuid = bytes_to_uuid(parsed['node_id'])
                print(f"✓ Discovered peer: {str(node_uuid)[:8]} at {addr[0]}:{parsed['port']}")
                
            except Exception as e:
                await asyncio.sleep(0.1)
    
    async def _cleanup_loop(self):
        """Remove stale peers and old challenges"""
        while True:
            await asyncio.sleep(30)
            
            now = time.time()
            
            # Remove stale peers (not seen in 15s)
            async with self._peers_lock:
                stale = [
                    node_id for node_id, (_, _, ts) in self.peers.items()
                    if now - ts > 15
                ]
                for node_id in stale:
                    del self.peers[node_id]
            
            # Limit challenge set size
            async with self._challenges_lock:
                if len(self._seen_challenges) > 10000:
                    self._seen_challenges.clear()
    
    async def get_peers(self):
        """Get current peer list"""
        async with self._peers_lock:
            return {
                node_id: (ip, port) 
                for node_id, (ip, port, _) in self.peers.items()
            }

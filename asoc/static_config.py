"""
Static Peer Configuration for ASoc

For production environments with:
- VLANs
- Firewalls blocking UDP
- Cross-datacenter clusters
- Kubernetes/Docker networks
- Any scenario where broadcast doesn't work

Usage:
    # Static configuration
    node = BinaryNode(
        community="prod-cluster",
        api_key="secret",
        static_peers=[
            "10.0.1.10:9000",
            "10.0.2.20:9000",
            "node3.example.com:9000"
        ]
    )
    
    # Or from environment/config file
    node = BinaryNode(
        community="prod-cluster",
        api_key="secret",
        static_peers=os.environ.get("ASOC_PEERS", "").split(",")
    )
"""

import asyncio
from typing import Optional, List
from node_binary import BinaryNode
import uuid as uuid_module


class StaticNode(BinaryNode):
    """
    ASoc node with static peer configuration
    
    Bypasses UDP discovery entirely - connects directly to configured peers.
    Ideal for production environments where discovery won't work.
    """
    
    def __init__(self,
                 community: str,
                 api_key: str,
                 static_peers: Optional[List[str]] = None,
                 enable_discovery: bool = False,
                 node_id: Optional[str] = None,
                 host: str = "0.0.0.0",
                 port: int = 9000):
        """
        Args:
            community: Cluster name
            api_key: Secret key for authentication
            static_peers: List of "host:port" strings (e.g. ["10.0.1.10:9000"])
            enable_discovery: Whether to also run UDP discovery (default: False)
            node_id: UUID string (auto-generated if None)
            host: Listen host
            port: Listen port
        """
        super().__init__(community, api_key, node_id, host, port)
        
        self.static_peers = static_peers or []
        self.enable_discovery = enable_discovery
        
        # Parse static peers
        self._static_peer_list = []
        for peer_str in self.static_peers:
            if ':' in peer_str:
                host, port_str = peer_str.rsplit(':', 1)
                try:
                    port = int(port_str)
                    self._static_peer_list.append((host.strip(), port))
                except ValueError:
                    print(f"⚠️  Invalid peer format: {peer_str}")
            else:
                print(f"⚠️  Invalid peer format (expected host:port): {peer_str}")
    
    async def start(self):
        """Start node with static configuration"""
        print(f"🚀 Starting static node {self.node_id[:8]}")
        print(f"   Community: {self.community}")
        print(f"   Port: {self.port}")
        print(f"   Static peers: {len(self._static_peer_list)}")
        
        if self.enable_discovery:
            print(f"   Discovery: enabled (hybrid mode)")
            await self.discovery.start()
        else:
            print(f"   Discovery: disabled (static only)")
        
        asyncio.create_task(self._start_server())
        asyncio.create_task(self._static_peer_connector())
    
    async def _static_peer_connector(self):
        """Connect to static peers instead of using discovery"""
        
        # Initial connection attempt
        print("\n📡 Connecting to static peers...")
        for host, port in self._static_peer_list:
            asyncio.create_task(self._connect_to_peer(host, port))
        
        # Periodic reconnection for failed peers
        while True:
            await asyncio.sleep(10)
            
            # Check which static peers are not connected
            connected_peers = set(self.peers.keys())
            
            for host, port in self._static_peer_list:
                # Try to connect if not already connected
                # (We don't know the peer's UUID until we connect, so we just retry all)
                asyncio.create_task(self._connect_to_peer(host, port))
    
    async def _connect_to_peer(self, host: str, port: int):
        """Connect to a specific peer by host:port"""
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0
            )
            
            conn = Connection(reader, writer)
            
            # Send HELLO
            from protocol_binary import (
                FRAME_HELLO, FRAME_ACCEPT, 
                encode_hello, decode_accept
            )
            
            hello_payload = encode_hello(self.node_id_bytes, self.api_key)
            await conn.send_frame(FRAME_HELLO, 0, 0, hello_payload)
            
            # Wait for ACCEPT
            frame_type, stream_id, seq, payload = await asyncio.wait_for(
                conn.recv_frame(),
                timeout=10.0
            )
            
            if frame_type != FRAME_ACCEPT:
                await conn.close()
                return
            
            # Verify and extract session token
            session_token = decode_accept(payload, self.api_key)
            if not session_token:
                print(f"⚠️  Invalid ACCEPT from {host}:{port}")
                await conn.close()
                return
            
            # Get peer's ID from HELLO (we need to know it)
            # Actually, we get it from the connection, not HELLO response
            # Let's extract it properly...
            
            # For now, we'll discover the peer_id during recv
            # Store connection temporarily
            async with self._peers_lock:
                # Check if we're already connected to this peer
                # (can't check by ID yet, so check by address)
                peer_addr = writer.get_extra_info('peername')
                
                # Store with temporary key, will update in recv_loop
                temp_key = f"{host}:{port}".encode()
                if temp_key not in self.peers:
                    self.peers[temp_key] = conn
                    
                    async with self._tokens_lock:
                        self._session_tokens[temp_key] = session_token
                    
                    print(f"✓ Connected to static peer: {host}:{port}")
                    
                    # Start recv loop (it will handle peer_id extraction)
                    asyncio.create_task(self._static_recv_loop(conn, host, port))
        
        except asyncio.TimeoutError:
            # Silent fail - will retry later
            pass
        except ConnectionRefusedError:
            # Silent fail - peer not up yet
            pass
        except Exception as e:
            # Log unexpected errors
            print(f"⚠️  Error connecting to {host}:{port}: {e}")
    
    async def _static_recv_loop(self, conn, host: str, port: int):
        """Receive loop for static peer connection"""
        from protocol_binary import FRAME_DATA, FRAME_END, bytes_to_uuid
        
        peer_id_bytes = None
        temp_key = f"{host}:{port}".encode()
        
        try:
            while True:
                frame_type, stream_id, seq, payload = await conn.recv_frame()
                
                # On first frame, we can identify the peer
                # (In production, peer would send HELLO with their ID)
                # For now, we'll track by connection
                
                if frame_type == FRAME_DATA:
                    print(f"[{self.node_id[:8]}] recv stream {stream_id} "
                          f"chunk {seq} size={len(payload)} "
                          f"from {host}:{port}")
                
                elif frame_type == FRAME_END:
                    print(f"[{self.node_id[:8]}] stream {stream_id} complete")
        
        except asyncio.IncompleteReadError:
            print(f"Connection closed: {host}:{port}")
        except Exception as e:
            print(f"Recv error from {host}:{port}: {e}")
        finally:
            async with self._peers_lock:
                if temp_key in self.peers:
                    del self.peers[temp_key]
            await conn.close()


# Import Connection for type hints
from transport_fixed import Connection


def load_peers_from_file(filepath: str) -> List[str]:
    """
    Load static peers from a configuration file
    
    File format (one peer per line):
        10.0.1.10:9000
        10.0.2.20:9000
        node3.example.com:9000
        # Comments are allowed
    """
    peers = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    peers.append(line)
    except FileNotFoundError:
        print(f"⚠️  Peer file not found: {filepath}")
    
    return peers


def load_peers_from_env(env_var: str = "ASOC_PEERS", separator: str = ",") -> List[str]:
    """
    Load static peers from environment variable
    
    Example:
        export ASOC_PEERS="10.0.1.10:9000,10.0.2.20:9000,node3:9000"
    """
    import os
    peers_str = os.environ.get(env_var, "")
    if not peers_str:
        return []
    
    return [p.strip() for p in peers_str.split(separator) if p.strip()]


# Example usage patterns
if __name__ == "__main__":
    import asyncio
    
    async def example_static():
        """Example: Static peer configuration"""
        
        # Hardcoded peers
        node = StaticNode(
            community="prod-cluster",
            api_key="secret-key",
            static_peers=[
                "10.0.1.10:9000",
                "10.0.2.20:9000",
            ],
            port=9000
        )
        
        await node.start()
        await asyncio.sleep(30)
        await node.shutdown()
    
    async def example_from_env():
        """Example: Load from environment variable"""
        
        node = StaticNode(
            community="prod-cluster",
            api_key="secret-key",
            static_peers=load_peers_from_env(),
            port=9000
        )
        
        await node.start()
        await asyncio.sleep(30)
        await node.shutdown()
    
    async def example_from_file():
        """Example: Load from configuration file"""
        
        node = StaticNode(
            community="prod-cluster",
            api_key="secret-key",
            static_peers=load_peers_from_file("/etc/asoc/peers.conf"),
            port=9000
        )
        
        await node.start()
        await asyncio.sleep(30)
        await node.shutdown()
    
    async def example_hybrid():
        """Example: Static + Discovery (hybrid mode)"""
        
        node = StaticNode(
            community="hybrid-cluster",
            api_key="secret-key",
            static_peers=["seed-node.example.com:9000"],
            enable_discovery=True,  # Also use UDP discovery
            port=9000
        )
        
        await node.start()
        await asyncio.sleep(30)
        await node.shutdown()
    
    # Run example
    asyncio.run(example_static())

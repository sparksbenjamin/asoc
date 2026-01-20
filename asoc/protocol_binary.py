import struct
import secrets
import hmac
import hashlib

VERSION = 1

# Frame types (1 byte)
FRAME_DATA = 1
FRAME_END = 2
FRAME_CONTROL = 3
FRAME_HELLO = 4
FRAME_ACCEPT = 5

# Header format: 14 bytes (no strings!)
# version (1) | type (1) | stream_id (4) | seq (4) | length (4)
HEADER_FMT = "!BBIII"
HEADER_SIZE = 14

def encode_frame(frame_type, stream_id, seq, payload: bytes):
    """Encode a frame - pure binary, no strings"""
    header = struct.pack(HEADER_FMT, VERSION, frame_type, stream_id, seq, len(payload))
    return header + payload

def decode_header(data: bytes):
    """Decode frame header"""
    return struct.unpack(HEADER_FMT, data)


# ============================================================================
# HELLO Frame (36 bytes total)
# ============================================================================
# node_id: 16 bytes (UUID as binary, not string!)
# api_key_proof: 16 bytes (HMAC-SHA256 truncated to 128 bits)
# challenge: 4 bytes (random uint32)
# ============================================================================

def encode_hello(node_id_bytes: bytes, api_key: bytes, challenge: int = None) -> bytes:
    """
    Encode HELLO frame
    
    Args:
        node_id_bytes: 16 bytes UUID (use uuid.uuid4().bytes)
        api_key: API key bytes
        challenge: Optional challenge (auto-generated if None)
    
    Returns:
        36 bytes: node_id(16) + hmac(16) + challenge(4)
    """
    if len(node_id_bytes) != 16:
        raise ValueError("node_id must be 16 bytes")
    
    if challenge is None:
        challenge = secrets.randbits(32)
    
    # Create HMAC proof (truncate to 16 bytes for compactness)
    data = node_id_bytes + struct.pack('!I', challenge)
    signature = hmac.new(api_key, data, hashlib.sha256).digest()[:16]
    
    return node_id_bytes + signature + struct.pack('!I', challenge)

def decode_hello(payload: bytes) -> tuple[bytes, bytes, int]:
    """
    Decode HELLO frame
    
    Returns:
        (node_id_bytes, signature, challenge)
    """
    if len(payload) != 36:
        raise ValueError(f"HELLO payload must be 36 bytes, got {len(payload)}")
    
    node_id = payload[:16]
    signature = payload[16:32]
    challenge = struct.unpack('!I', payload[32:36])[0]
    
    return node_id, signature, challenge

def verify_hello(payload: bytes, api_key: bytes) -> bool:
    """Verify HELLO HMAC signature"""
    node_id, signature, challenge = decode_hello(payload)
    
    # Recompute HMAC
    data = node_id + struct.pack('!I', challenge)
    expected = hmac.new(api_key, data, hashlib.sha256).digest()[:16]
    
    return hmac.compare_digest(expected, signature)


# ============================================================================
# ACCEPT Frame (16 bytes total)
# ============================================================================
# session_token: 8 bytes (random)
# token_signature: 8 bytes (HMAC truncated)
# ============================================================================

def encode_accept(api_key: bytes) -> tuple[bytes, bytes]:
    """
    Encode ACCEPT frame with session token
    
    Returns:
        (payload, session_token) where payload is 16 bytes
    """
    # Generate random 8-byte token
    session_token = secrets.token_bytes(8)
    
    # Sign it (truncate HMAC to 8 bytes)
    signature = hmac.new(api_key, session_token, hashlib.sha256).digest()[:8]
    
    payload = session_token + signature
    return payload, session_token

def decode_accept(payload: bytes, api_key: bytes) -> bytes:
    """
    Decode and verify ACCEPT frame
    
    Returns:
        session_token (8 bytes) if valid, None if invalid
    """
    if len(payload) != 16:
        raise ValueError(f"ACCEPT payload must be 16 bytes, got {len(payload)}")
    
    session_token = payload[:8]
    signature = payload[8:16]
    
    # Verify signature
    expected = hmac.new(api_key, session_token, hashlib.sha256).digest()[:8]
    
    if hmac.compare_digest(expected, signature):
        return session_token
    return None


# ============================================================================
# Discovery Message (binary, not JSON!)
# ============================================================================
# community_hash: 8 bytes (SHA256 hash of community string, truncated)
# node_id: 16 bytes (UUID binary)
# port: 2 bytes (uint16)
# timestamp: 4 bytes (uint32, seconds since epoch)
# challenge: 4 bytes (uint32)
# signature: 16 bytes (HMAC of above fields)
# Total: 50 bytes (vs ~150 for JSON!)
# ============================================================================

def encode_discovery(community: str, node_id_bytes: bytes, port: int, 
                     api_key: bytes, timestamp: int = None, challenge: int = None) -> bytes:
    """
    Encode discovery broadcast message (binary, not JSON!)
    
    Returns:
        50 bytes total
    """
    import time
    
    if timestamp is None:
        timestamp = int(time.time())
    if challenge is None:
        challenge = secrets.randbits(32)
    
    # Hash community string to 8 bytes
    community_hash = hashlib.sha256(community.encode()).digest()[:8]
    
    # Pack all fields
    message = (
        community_hash +                    # 8 bytes
        node_id_bytes +                     # 16 bytes
        struct.pack('!H', port) +           # 2 bytes
        struct.pack('!I', timestamp) +      # 4 bytes
        struct.pack('!I', challenge)        # 4 bytes
    )
    
    # Sign it (truncate to 16 bytes)
    signature = hmac.new(api_key, message, hashlib.sha256).digest()[:16]
    
    return message + signature

def decode_discovery(payload: bytes, expected_community: str, api_key: bytes) -> dict:
    """
    Decode and verify discovery message
    
    Returns:
        dict with parsed fields if valid, None if invalid
    """
    if len(payload) != 50:
        return None
    
    # Parse fields
    community_hash = payload[:8]
    node_id = payload[8:24]
    port = struct.unpack('!H', payload[24:26])[0]
    timestamp = struct.unpack('!I', payload[26:30])[0]
    challenge = struct.unpack('!I', payload[30:34])[0]
    signature = payload[34:50]
    
    # Verify community
    expected_hash = hashlib.sha256(expected_community.encode()).digest()[:8]
    if not hmac.compare_digest(community_hash, expected_hash):
        return None
    
    # Verify signature
    message = payload[:34]
    expected_sig = hmac.new(api_key, message, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(signature, expected_sig):
        return None
    
    return {
        'node_id': node_id,
        'port': port,
        'timestamp': timestamp,
        'challenge': challenge
    }


# ============================================================================
# Utility: Convert between UUID and bytes
# ============================================================================

import uuid as uuid_module

def uuid_to_bytes(uuid_obj: uuid_module.UUID) -> bytes:
    """Convert UUID to 16 bytes"""
    return uuid_obj.bytes

def bytes_to_uuid(uuid_bytes: bytes) -> uuid_module.UUID:
    """Convert 16 bytes to UUID"""
    return uuid_module.UUID(bytes=uuid_bytes)

def uuid_str_to_bytes(uuid_str: str) -> bytes:
    """Convert UUID string to 16 bytes"""
    return uuid_module.UUID(uuid_str).bytes


# ============================================================================
# Size Comparison
# ============================================================================

def size_comparison():
    """Compare sizes: JWT vs Binary"""
    
    print("=" * 60)
    print("Protocol Size Comparison")
    print("=" * 60)
    
    # JWT approach
    jwt_discovery = 150  # Typical JSON discovery message
    jwt_hello = 100      # node_id + JWT (~64 chars base64)
    jwt_accept = 200     # Full JWT token
    jwt_total = jwt_discovery + jwt_hello + jwt_accept
    
    # Binary approach
    bin_discovery = 50   # Compact binary
    bin_hello = 36       # UUID(16) + HMAC(16) + challenge(4)
    bin_accept = 16      # token(8) + signature(8)
    bin_total = bin_discovery + bin_hello + bin_accept
    
    print(f"\nDiscovery Message:")
    print(f"  JWT/JSON:  {jwt_discovery:3d} bytes")
    print(f"  Binary:    {bin_discovery:3d} bytes  ({100*(jwt_discovery-bin_discovery)/jwt_discovery:.0f}% smaller)")
    
    print(f"\nHELLO Frame:")
    print(f"  JWT:       {jwt_hello:3d} bytes")
    print(f"  Binary:    {bin_hello:3d} bytes  ({100*(jwt_hello-bin_hello)/jwt_hello:.0f}% smaller)")
    
    print(f"\nACCEPT Frame:")
    print(f"  JWT:       {jwt_accept:3d} bytes")
    print(f"  Binary:    {bin_accept:3d} bytes  ({100*(jwt_accept-bin_accept)/jwt_accept:.0f}% smaller)")
    
    print(f"\n{'─'*60}")
    print(f"Total Handshake:")
    print(f"  JWT:       {jwt_total:3d} bytes")
    print(f"  Binary:    {bin_total:3d} bytes  ({100*(jwt_total-bin_total)/jwt_total:.0f}% smaller)")
    print(f"\n{'─'*60}")
    
    print(f"\nData Frame (1MB tensor):")
    print(f"  Header:    {HEADER_SIZE} bytes")
    print(f"  Token:     0 bytes  (connection already authenticated!)")
    print(f"  Data:      1,048,576 bytes")
    print(f"  Total:     1,048,590 bytes")
    print(f"  Overhead:  0.001%")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    size_comparison()

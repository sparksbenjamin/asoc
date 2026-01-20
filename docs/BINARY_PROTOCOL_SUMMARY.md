# ASoc Ultra-Compact Binary Protocol

## The Problem with JWT/Strings

**JWT approach:**
- Discovery: ~150 bytes (JSON with strings)
- HELLO: ~100 bytes (UUID string + JWT)
- ACCEPT: ~200 bytes (full JWT token)
- **Total: 450 bytes**
- Data frames: Need token verification

**Problems:**
- Strings waste space (UUID string is 36 chars vs 16 bytes binary)
- Base64 encoding adds 33% overhead
- JSON adds delimiters, whitespace
- Per-frame token validation costs CPU

## Binary Protocol Solution

### Message Sizes

**Discovery: 50 bytes** (67% smaller)
```
Community hash:  8 bytes  (SHA256 truncated)
Node ID:        16 bytes  (UUID binary)
Port:            2 bytes  (uint16)
Timestamp:       4 bytes  (uint32)
Challenge:       4 bytes  (uint32)
Signature:      16 bytes  (HMAC truncated)
────────────────────────
Total:          50 bytes
```

**HELLO: 36 bytes** (64% smaller)
```
Node ID:        16 bytes  (UUID binary)
Signature:      16 bytes  (HMAC proof)
Challenge:       4 bytes  (uint32)
────────────────────────
Total:          36 bytes
```

**ACCEPT: 16 bytes** (92% smaller!)
```
Session token:   8 bytes  (random)
Signature:       8 bytes  (HMAC truncated)
────────────────────────
Total:          16 bytes
```

**Total Handshake: 102 bytes** (vs 450 = **77% reduction**)

### Data Frames: ZERO Token Overhead

**Key insight:** TCP connections are already stateful. Once authenticated during handshake, no need for tokens in every frame!

```
Header:         14 bytes  (version, type, stream_id, seq, length)
Token:           0 bytes  (connection already authenticated!)
Data:            N bytes  (pure tensor data)
────────────────────────
Overhead:   0.001% for 1MB frames
```

## Code Comparison

### Old Way (JWT)
```python
# Discovery message
msg = json.dumps({
    "community": "my-cluster",      # String
    "node_id": str(uuid.uuid4()),   # String (36 chars)
    "port": 9000,
    "signature": jwt_token          # ~200 bytes
})
# Result: ~150 bytes
```

### New Way (Binary)
```python
# Discovery message  
msg = encode_discovery(
    community,       # Hashed to 8 bytes
    uuid.bytes,      # 16 bytes binary
    port,            # 2 bytes
    api_key
)
# Result: 50 bytes
```

## Benefits

1. **Bandwidth Savings**
   - 77% smaller handshake
   - 0 overhead in data frames
   - Matters for high-frequency connections

2. **CPU Savings**
   - No JSON parsing
   - No base64 encoding/decoding
   - No per-frame crypto verification
   - Just memcpy and HMAC on handshake

3. **Memory Savings**
   - UUIDs as 16 bytes vs 36 chars
   - Tokens as 8 bytes vs 200
   - No string allocations

4. **Speed**
   - Binary parsing = pointer arithmetic
   - No string parsing
   - No regex, no character validation

## Security

**Still secure:**
- HMAC-SHA256 for signatures (just truncated to 16 bytes)
- Challenge-response prevents replay
- Connection authentication sufficient (like TLS)
- Optional: Add TLS wrapper for encryption

**What changed:**
- Removed JWT complexity
- Truncated HMACs (128-bit still secure)
- No tokens after handshake

## Performance Target

With this protocol:
- **Latency:** ~50μs per chunk (just memcpy + TCP)
- **Throughput:** Network-limited (can saturate 10GbE)
- **CPU:** <2% for streaming
- **Overhead:** 0.001% for 1MB frames

**vs gRPC:**
- gRPC: ~500μs per message (protobuf + HTTP/2)
- ASoc: ~50μs (binary framing only)
- **10x faster**

## Usage

```python
from node_binary import BinaryNode

# Same simple API, way more efficient
node = BinaryNode(
    community="my-cluster",
    api_key="secret-key"
)

await node.start()

# Stream tensor (no token overhead!)
await node.stream_tensor(peer_id, tensor_bytes, tensor_id=1)
```

## Files

- `protocol_binary.py` - Binary encoding/decoding
- `discovery_binary.py` - 50-byte discovery messages  
- `node_binary.py` - Complete binary node implementation
- `example_binary.py` - Working examples

## Recommendation

**Use the binary protocol.** It's:
- Simpler (no JWT library needed)
- Faster (no string parsing)
- Smaller (77% less overhead)
- Still secure (HMAC + connection auth)

The JWT version was educational, but this is what you ship.

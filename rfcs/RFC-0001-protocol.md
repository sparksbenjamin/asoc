# RFC-0001: ASoc Core Protocol Specification

**Status:** Implemented  
**Version:** 0.1.0  
**Date:** January 2025  
**Author:** Benjamin Sparks  
**Implementation:** https://github.com/sparksbenjamin/asoc

---

## Abstract

ASoc (AI Socket) is an ultra-compact, peer-to-peer protocol for streaming tensors between distributed AI compute nodes. This document specifies the wire format, connection semantics, and operational characteristics of the ASoc protocol. The design prioritizes minimal overhead (0.001% on data frames), simplicity (zero dependencies), and performance (near line-rate throughput).

## Table of Contents

1. [Introduction](#1-introduction)
2. [Terminology](#2-terminology)
3. [Protocol Overview](#3-protocol-overview)
4. [Discovery Phase](#4-discovery-phase)
5. [Connection Phase](#5-connection-phase)
6. [Streaming Phase](#6-streaming-phase)
7. [Frame Format](#7-frame-format)
8. [State Machine](#8-state-machine)
9. [Error Handling](#9-error-handling)
10. [Security Considerations](#10-security-considerations)
11. [Performance Characteristics](#11-performance-characteristics)
12. [IANA Considerations](#12-iana-considerations)
13. [References](#13-references)

---

## 1. Introduction

### 1.1 Motivation

Modern distributed AI training requires efficient tensor streaming between compute nodes. Existing solutions present significant challenges:

- **MPI**: Complex configuration (hostfiles, rank management), steep learning curve
- **NCCL**: NVIDIA GPU lock-in, single-datacenter limitation
- **gRPC**: HTTP/2 overhead, protobuf compilation, large handshake (450+ bytes)
- **Custom Solutions**: Each framework reinvents the wheel

ASoc addresses these challenges by providing a minimal, framework-agnostic protocol that:
- Requires zero configuration for local clusters (UDP discovery)
- Supports static configuration for production (firewalls, VLANs, HPC)
- Achieves near line-rate performance (0.001% overhead)
- Uses binary framing (102-byte handshake vs 450+ for JWT)
- Has zero dependencies (pure Python asyncio)

### 1.2 Design Goals

1. **Simplicity**: 3 lines of code to start streaming
2. **Performance**: Minimal protocol overhead, saturate 10 GbE networks
3. **Portability**: Works across clouds, heterogeneous hardware
4. **Security**: HMAC authentication, replay protection
5. **Scalability**: Support 2-1000+ nodes
6. **Framework Agnostic**: Not tied to PyTorch, TensorFlow, JAX, etc.

### 1.3 Non-Goals

- **Replace NCCL on InfiniBand**: NCCL is optimized for single-datacenter GPU clusters
- **Implement MPI semantics**: No collective operations, ranks, or barriers
- **Provide compression**: Applications can compress before streaming
- **Built-in encryption**: Use TLS wrapper if needed

---

## 2. Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119.

**Node**: An ASoc peer capable of sending and receiving tensor data

**Community**: A cluster identifier used for namespace isolation (like WiFi SSID)

**API Key**: A shared secret used for HMAC authentication (like WiFi password)

**Session Token**: An 8-byte opaque value issued after successful authentication

**Stream**: A unidirectional flow of tensor chunks identified by a stream ID

**Frame**: The basic protocol unit consisting of header + payload

**Chunk**: A portion of a tensor, transmitted in a single DATA frame

---

## 3. Protocol Overview

### 3.1 Three-Phase Design

ASoc operates in three distinct phases:

```
┌─────────────────────────────────────────┐
│  Phase 1: Discovery (UDP)               │
│  - Broadcast presence                   │
│  - Exchange node IDs                    │
│  - HMAC proof of API key                │
│  - 50 bytes per message                 │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Phase 2: Connection (TCP)              │
│  - HELLO: 36 bytes (UUID + HMAC)        │
│  - ACCEPT: 16 bytes (session token)     │
│  - Total: 52 bytes                      │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Phase 3: Streaming (TCP)               │
│  - DATA frames: 14-byte header          │
│  - No per-frame authentication          │
│  - TCP provides reliability             │
└─────────────────────────────────────────┘
```

### 3.2 Connection Model

ASoc uses a **stateless-after-handshake** model:
- Authentication occurs once during connection establishment
- Session tokens are issued but NOT required in data frames
- TCP connection itself proves identity (like TLS)
- Eliminates per-frame cryptographic overhead

### 3.3 Transport Binding

- **Discovery**: UDP port 9999 (default, configurable)
- **Data Transport**: TCP port 9000 (default, configurable)
- **Rationale**: UDP for broadcast discovery, TCP for reliable data delivery

---

## 4. Discovery Phase

### 4.1 Overview

Discovery allows nodes to find peers on the same network segment without configuration. It is OPTIONAL; static peer configuration bypasses this phase.

### 4.2 Discovery Message Format

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Community Hash (8 bytes)                  |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Node UUID (16 bytes)                    |
|                                                               |
|                                                               |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Port (2 bytes)      |      Timestamp (4 bytes)      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Challenge (4 bytes)                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    HMAC Signature (16 bytes)                  |
|                                                               |
|                                                               |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Total: 50 bytes
```

### 4.3 Field Descriptions

**Community Hash (8 bytes)**
- SHA256(community_string) truncated to 64 bits
- Provides namespace isolation
- Not a secret; similar to WiFi SSID

**Node UUID (16 bytes)**
- RFC 4122 UUID in binary form
- Uniquely identifies the node
- Generated once per node instance

**Port (2 bytes)**
- TCP port number (big-endian uint16)
- Where node listens for connections
- Typically 9000

**Timestamp (4 bytes)**
- Unix epoch seconds (big-endian uint32)
- Used for message freshness
- Messages older than 60 seconds SHOULD be rejected

**Challenge (4 bytes)**
- Random 32-bit value (big-endian uint32)
- Used for replay protection
- MUST be unique per message

**HMAC Signature (16 bytes)**
- HMAC-SHA256(api_key, message_bytes[0:34]) truncated to 128 bits
- Proves knowledge of API key without transmitting it
- Computed over all fields except signature itself

### 4.4 Discovery Protocol

1. Node broadcasts discovery message every 3 seconds (default)
2. Receiving nodes:
   - Verify community hash matches
   - Verify HMAC signature
   - Check challenge not seen before (replay protection)
   - Record peer (node_id, ip, port)
3. Stale peers (>15 seconds since last message) are removed

### 4.5 Static Configuration

In production environments (HPC, firewalls, VLANs), static peer configuration bypasses discovery:

```python
node = ASocNode(
    community="cluster",
    api_key="secret",
    static_peers=["10.0.1.10:9000", "10.0.2.20:9000"],
    enable_discovery=False  # Disable UDP broadcast
)
```

---

## 5. Connection Phase

### 5.1 Overview

Once peers are discovered (or configured), nodes establish TCP connections for data streaming. Connection establishment uses a two-message handshake.

### 5.2 HELLO Frame

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Ver |  Type   |           Stream ID (4 bytes)                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Sequence (4 bytes)                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Length (4 bytes)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Node UUID (16 bytes)                       |
|                                                               |
|                                                               |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                 HMAC Signature (16 bytes)                     |
|                                                               |
|                                                               |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   Challenge (4 bytes)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Frame Header: 14 bytes
Payload: 36 bytes (UUID + Signature + Challenge)
Total: 50 bytes
```

**Fields:**
- **Version**: 1 (4 bits)
- **Type**: FRAME_HELLO = 4 (4 bits)
- **Stream ID**: 0 (handshake)
- **Sequence**: 0 (handshake)
- **Length**: 36 (payload size)
- **Node UUID**: Sender's UUID
- **HMAC Signature**: HMAC-SHA256(api_key, uuid + challenge) truncated to 128 bits
- **Challenge**: Random 32-bit value

### 5.3 ACCEPT Frame

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Ver |  Type   |           Stream ID (4 bytes)                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Sequence (4 bytes)                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Length (4 bytes)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  Session Token (8 bytes)                      |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|              Token Signature (8 bytes)                        |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Frame Header: 14 bytes
Payload: 16 bytes (Token + Signature)
Total: 30 bytes
```

**Fields:**
- **Version**: 1
- **Type**: FRAME_ACCEPT = 5
- **Stream ID**: 0
- **Sequence**: 0
- **Length**: 16
- **Session Token**: Random 8-byte value
- **Token Signature**: HMAC-SHA256(api_key, token) truncated to 64 bits

### 5.4 Connection Establishment Flow

```
Client                                Server
  |                                     |
  |-------- TCP SYN ------------------>|
  |<------- TCP SYN-ACK ---------------|
  |-------- TCP ACK ------------------>|
  |                                     |
  |-------- HELLO Frame --------------->|
  |         (36 bytes payload)          |
  |                                     |
  |         [Server verifies HMAC]      |
  |         [Server generates token]    |
  |                                     |
  |<------- ACCEPT Frame ---------------|
  |         (16 bytes payload)          |
  |                                     |
  |     [Client verifies signature]     |
  |     [Connection established]        |
  |                                     |
  |<======= DATA Frames ===============>|
```

**Total Handshake Overhead:** 52 bytes (HELLO payload 36 + ACCEPT payload 16)

**Comparison:**
- ASoc: 52 bytes
- JWT/gRPC: 450+ bytes
- Savings: 88%

---

## 6. Streaming Phase

### 6.1 Overview

After authentication, nodes can stream tensor data. Each stream is identified by a unique stream ID and consists of DATA frames followed by an END frame.

### 6.2 Stream Lifecycle

```
Stream Start → DATA (seq=0) → DATA (seq=1) → ... → DATA (seq=N) → END → Stream Complete
```

### 6.3 Stream ID Allocation

- **Client-initiated streams**: Odd numbers (1, 3, 5, ...)
- **Server-initiated streams**: Even numbers (2, 4, 6, ...)
- **Auto-increment**: Each node maintains a counter for its streams
- **Range**: 0 reserved for handshake, 1-4,294,967,295 for data

### 6.4 Chunking

Large tensors are split into chunks (default 1 MB):

```
Tensor (100 MB) → 100 chunks × 1 MB → 100 DATA frames
```

**Rationale:**
- Prevents head-of-line blocking
- Allows concurrent streams
- Provides flow control via TCP backpressure
- Enables progress tracking

---

## 7. Frame Format

### 7.1 Frame Header (All Frame Types)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Ver |  Type   |           Stream ID (4 bytes)                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Sequence Number (4 bytes)                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   Payload Length (4 bytes)                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Payload (variable)                        |
|                          ...                                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Header: 14 bytes (fixed)
Payload: 0 to 2^32-1 bytes (variable)
```

### 7.2 Frame Header Fields

**Version (4 bits)**
- Current version: 1
- Future versions maintain backward compatibility

**Type (4 bits)**
- FRAME_DATA = 1 (data chunk)
- FRAME_END = 2 (stream end marker)
- FRAME_CONTROL = 3 (reserved for future control messages)
- FRAME_HELLO = 4 (connection handshake)
- FRAME_ACCEPT = 5 (connection acceptance)
- Values 6-15 reserved

**Stream ID (32 bits, big-endian)**
- Identifies which stream this frame belongs to
- 0 reserved for handshake
- 1-4,294,967,295 for data streams

**Sequence Number (32 bits, big-endian)**
- Monotonically increasing within a stream
- Starts at 0 for first DATA frame
- Increments by 1 for each subsequent frame
- Allows receiver to detect missing frames (though TCP prevents this)

**Payload Length (32 bits, big-endian)**
- Number of bytes in payload
- 0 is valid (e.g., END frame)
- Maximum: 2^32-1 bytes (4 GB per frame)
- Typical: 1,048,576 bytes (1 MB)

### 7.3 DATA Frame

```
Header (14 bytes) + Tensor Chunk (variable)
```

**No authentication overhead**: Connection already authenticated

**Example (1 MB chunk):**
```
Version: 1
Type: FRAME_DATA (1)
Stream ID: 123
Sequence: 0
Length: 1,048,576
Payload: [1 MB of tensor data]

Total: 14 + 1,048,576 = 1,048,590 bytes
Overhead: 14 / 1,048,590 = 0.00133% ≈ 0.001%
```

### 7.4 END Frame

```
Header (14 bytes) + Empty Payload
```

Signals stream completion:
```
Version: 1
Type: FRAME_END (2)
Stream ID: 123
Sequence: 100 (last seq + 1)
Length: 0
Payload: (none)
```

Receiver MUST close stream after END frame.

### 7.5 Frame Size Limits

- **Minimum**: 14 bytes (header only, valid for END frames)
- **Maximum**: 4 GB (2^32-1 bytes payload + 14 byte header)
- **Recommended**: 1 MB chunks for optimal throughput/latency balance

---

## 8. State Machine

### 8.1 Connection States

```
                    ┌─────────────┐
                    │   CLOSED    │
                    └──────┬──────┘
                           │ connect()
                           ↓
                    ┌─────────────┐
              ┌─────┤ CONNECTING  │
              │     └──────┬──────┘
              │ timeout    │ HELLO sent
              │            ↓
              │     ┌─────────────┐
              │     │ WAIT_ACCEPT │
              │     └──────┬──────┘
              │ timeout    │ ACCEPT received
              │            ↓
              │     ┌─────────────┐
              └────→│ ESTABLISHED │
                    └──────┬──────┘
                           │ close() or error
                           ↓
                    ┌─────────────┐
                    │   CLOSED    │
                    └─────────────┘
```

### 8.2 Stream States

```
                    ┌─────────────┐
                    │    IDLE     │
                    └──────┬──────┘
                           │ send_tensor()
                           ↓
                    ┌─────────────┐
                    │   SENDING   │
                    └──────┬──────┘
                           │ last chunk + END
                           ↓
                    ┌─────────────┐
                    │   CLOSED    │
                    └─────────────┘
```

---

## 9. Error Handling

### 9.1 Authentication Failures

**Invalid HMAC Signature:**
- Server MUST close TCP connection immediately
- No error frame is sent
- Rationale: Prevents information leakage to attacker

**Mismatched Community:**
- Discovery message silently dropped
- No TCP connection established
- Rationale: Different communities = different clusters

### 9.2 Protocol Violations

**Invalid Frame Version:**
- Connection MUST be closed
- Future: Send CONTROL frame with error code

**Invalid Frame Type:**
- Frame MUST be ignored
- Connection remains open
- Rationale: Forward compatibility

**Invalid Sequence Number:**
- TCP guarantees ordering, so this indicates implementation bug
- Connection SHOULD be closed
- Log error for debugging

### 9.3 Timeout Handling

**Connection Timeout:**
- Default: 10 seconds for HELLO → ACCEPT
- Configurable per implementation
- After timeout, close TCP connection

**Send Timeout:**
- If `send()` blocks for >10 seconds, connection is likely dead
- Close connection and attempt reconnection

**Receive Timeout:**
- If no data received for >30 seconds on active stream, peer may be dead
- Close connection and attempt reconnection

### 9.4 Reconnection Strategy

On connection failure:
1. Close existing TCP connection
2. Wait random delay (1-5 seconds) to avoid thundering herd
3. Attempt reconnection
4. Exponential backoff on repeated failures (max 60 seconds)
5. For static peers, keep retrying indefinitely
6. For discovered peers, remove from peer list after 3 failures

---

## 10. Security Considerations

### 10.1 Threat Model

**Assumptions:**
- Nodes share a pre-established API key
- Network may be untrusted (e.g., shared datacenter)
- Eavesdropping is possible (use TLS wrapper if confidentiality needed)

**Protected Against:**
- Unauthorized node joining cluster ✅
- Replay attacks ✅
- Man-in-the-middle (with TLS) ✅
- Cluster mixing (via community string) ✅

**Not Protected Against:**
- Network-level DoS (use firewall rules)
- Compromised node with valid API key
- Eavesdropping (unless TLS wrapper used)

### 10.2 Authentication Properties

**HMAC-SHA256:**
- 256-bit security (truncated to 128 bits for compactness)
- 128 bits still provides 2^64 security against birthday attacks
- Acceptable for cluster authentication

**Challenge-Response:**
- Random 32-bit challenge prevents replay
- Challenge uniqueness checked per node
- Old challenges (>60 seconds) rejected

**Session Tokens:**
- 8-byte random value = 2^64 possible tokens
- Stateless (HMAC-signed)
- Not required in data frames (TCP connection proves identity)

### 10.3 Recommendations

**API Key Management:**
- Use strong random keys (32+ bytes)
- Rotate keys periodically (e.g., monthly)
- Never hardcode keys in source code
- Use environment variables or secrets managers

**Network Isolation:**
- Run ASoc in private VPC/VLAN when possible
- Use firewall rules to restrict access to TCP port
- For UDP discovery, restrict broadcast domain

**TLS Wrapper:**
- For cross-datacenter or sensitive data, wrap TCP in TLS:
  ```python
  ssl_context = ssl.create_default_context()
  reader, writer = await asyncio.open_connection(
      host, port, ssl=ssl_context
  )
  ```

### 10.4 Denial of Service

**Discovery Storm:**
- Limit discovery messages to 1 per 3 seconds per node
- Ignore discovery messages from same node within 1 second

**Connection Exhaustion:**
- Limit concurrent connections per node (e.g., 100)
- Close connections after 5 failed authentication attempts from same IP

**Large Frame Attack:**
- Enforce maximum frame size (e.g., 10 MB)
- Close connection if frame exceeds limit

---

## 11. Performance Characteristics

### 11.1 Measured Performance

**Benchmarked on Production HPC (SLURM, 10 GbE):**

| Metric | Value |
|--------|-------|
| Throughput (2 nodes) | 446 MB/s per peer |
| Throughput (8 nodes) | 100 MB/s per peer* |
| Latency (1 KB) | ~1-5 ms |
| Latency (1 MB) | ~10-20 ms |
| Protocol Overhead | 0.001% |
| CPU Usage | <2% during streaming |

*Single-sender bottleneck; all-to-all would be ~800 MB/s aggregate

### 11.2 Overhead Analysis

**Handshake:**
- ASoc: 52 bytes (HELLO + ACCEPT payload)
- gRPC/JWT: 450+ bytes
- Savings: 88%

**Data Frames:**
- ASoc: 14 bytes per frame (0.001% for 1 MB chunks)
- gRPC: ~200 bytes per frame (protobuf + HTTP/2)
- Savings: 93%

### 11.3 Scalability

**Connection Scaling:**
- Tested: 8 nodes, full mesh (56 connections)
- Theoretical: 1000 nodes = 499,500 connections (impractical)
- Recommended: Use hierarchical topologies for >100 nodes

**Bandwidth Scaling:**
- 2 nodes: Linear (892 MB/s aggregate)
- 8 nodes: NIC-limited (803 MB/s aggregate from single sender)
- Solution: All-to-all or ring topologies

### 11.4 Comparison to Alternatives

| Protocol | Handshake | Data Overhead | Setup Complexity | Vendor Lock-in |
|----------|-----------|---------------|------------------|----------------|
| ASoc | 52 bytes | 14 bytes | Low | None |
| gRPC | 450+ bytes | 200+ bytes | Medium | None |
| MPI | N/A | Variable | Very High | None |
| NCCL | N/A | Minimal | Medium | NVIDIA only |

---

## 12. IANA Considerations

This document requests the following port assignments:

- **UDP Port 9999**: ASoc Discovery Protocol (default, configurable)
- **TCP Port 9000**: ASoc Data Transport (default, configurable)

These are currently in the Dynamic/Private range (49152-65535) but could be assigned official ports if protocol gains adoption.

---

## 13. References

### 13.1 Normative References

- **RFC 2119**: Key words for use in RFCs to Indicate Requirement Levels
- **RFC 4122**: A Universally Unique IDentifier (UUID) URN Namespace
- **RFC 2104**: HMAC: Keyed-Hashing for Message Authentication

### 13.2 Informative References

- **WebSocket (RFC 6455)**: Inspiration for framing design
- **HTTP/2 (RFC 7540)**: Inspiration for binary protocol
- **QUIC (RFC 9000)**: Inspiration for stream multiplexing
- **SNMPv3 (RFC 3414)**: Inspiration for security model

### 13.3 Implementation

- **Reference Implementation**: https://github.com/sparksbenjamin/asoc
- **Language**: Python 3.7+
- **License**: MIT

---

## Appendix A: Frame Examples

### A.1 HELLO Frame (Hex Dump)

```
0000: 14 00 00 00 00 00 00 00  00 00 00 24 a1 b2 c3 d4   ...........$....
0010: e5 f6 07 18 29 3a 4b 5c  6d 7e 8f 90 a1 b2 c3 d4   ....):[m~......
0020: e5 f6 07 18 29 3a 4b 5c  6d 7e 8f 90 12 34 56 78   ....):[m~...4Vx
0030: 9a bc de f0                                        ....

Breakdown:
Byte 0: 0x14 = Version 1, Type 4 (HELLO)
Bytes 1-4: Stream ID = 0
Bytes 5-8: Sequence = 0
Bytes 9-12: Length = 36 (0x00000024)
Bytes 13-28: Node UUID
Bytes 29-44: HMAC Signature
Bytes 45-48: Challenge
```

### A.2 DATA Frame (Simplified)

```
0000: 11 00 00 00 7b 00 00 00  00 00 10 00 00 [tensor data...]
      ^^ Ver=1,Type=1
         ^^^^^^^^^^ Stream=123
                    ^^^^^^^^^^ Seq=0
                               ^^^^^^^^^^ Len=1048576
```

---

## Appendix B: Implementation Notes

### B.1 Asyncio Integration

ASoc is designed for Python's asyncio:

```python
async def send_frame(self, frame_type, stream_id, seq, payload):
    frame = encode_frame(frame_type, stream_id, seq, payload)
    self.writer.write(frame)
    await self.writer.drain()  # TCP backpressure
```

### B.2 Flow Control

- Use asyncio.Semaphore to limit concurrent sends
- `writer.drain()` provides TCP-level backpressure
- No application-level flow control needed

### B.3 Zero-Copy (Future)

Current implementation copies data. Future optimizations:
- Use `memoryview` for zero-copy slicing
- Support GPU-Direct RDMA for GPU tensors
- Use `sendfile()` for disk-to-network transfers

---

## Appendix C: Test Vectors

### C.1 HMAC Calculation

```python
import hmac
import hashlib

api_key = b"test-secret-key"
node_id = bytes.fromhex("a1b2c3d4e5f607182930a1b2c3d4e5f6")
challenge = 0x12345678

data = node_id + challenge.to_bytes(4, 'big')
signature = hmac.new(api_key, data, hashlib.sha256).digest()[:16]

# Expected signature (first 16 bytes):
# b'\xe4\x9a\x12\x7f\x...' (depends on key)
```

### C.2 Discovery Message

```python
community = "test-cluster"
community_hash = hashlib.sha256(community.encode()).digest()[:8]
# Expected: b'\x8c\xf2\x...' (depends on string)
```

---

**End of RFC-0001**

---

## Changelog

- **v0.1.0 (January 2025)**: Initial specification based on production implementation

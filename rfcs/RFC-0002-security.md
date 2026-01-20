# RFC-0002: ASoc Security Model

**Status:** Implemented  
**Version:** 0.1.0  
**Date:** January 2025  
**Author:** Benjamin Sparks  
**Extends:** RFC-0001  
**Implementation:** https://github.com/sparksbenjamin/asoc

---

## Abstract

This document specifies the security model for ASoc (AI Socket) protocol. The design is inspired by SNMPv3's three-layer authentication approach: community strings for namespace isolation, API keys for authentication, and session tokens for stateless operation. The goal is to provide strong security with minimal overhead (no per-frame crypto after handshake).

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Security Architecture](#2-security-architecture)
3. [Layer 1: Community String](#3-layer-1-community-string)
4. [Layer 2: API Key Authentication](#4-layer-2-api-key-authentication)
5. [Layer 3: Session Tokens](#5-layer-3-session-tokens)
6. [Threat Analysis](#6-threat-analysis)
7. [Cryptographic Algorithms](#7-cryptographic-algorithms)
8. [Key Management](#8-key-management)
9. [Security Considerations](#9-security-considerations)
10. [Future Extensions](#10-future-extensions)

---

## 1. Introduction

### 1.1 Design Philosophy

ASoc's security model balances three requirements:

1. **Strong Authentication**: Prevent unauthorized nodes from joining clusters
2. **Minimal Overhead**: No per-frame cryptographic operations during streaming
3. **Operational Simplicity**: Easy to deploy, no PKI infrastructure required

### 1.2 SNMPv3 Inspiration

The three-layer model is inspired by SNMPv3 (RFC 3414):

| Layer | SNMPv3 | ASoc |
|-------|--------|------|
| Layer 1 | Context | Community String |
| Layer 2 | User Auth | API Key (HMAC) |
| Layer 3 | Privacy | Session Tokens |

**Key Difference**: ASoc's Layer 3 is stateless (no per-frame crypto), leveraging TCP connection as proof of identity.

### 1.3 Security Goals

**Primary Goals:**
- Prevent unauthorized nodes from joining cluster ✅
- Prevent replay attacks ✅
- Provide namespace isolation ✅

**Non-Goals:**
- Confidentiality (use TLS wrapper if needed)
- Perfect forward secrecy (use TLS wrapper if needed)
- Certificate-based authentication (use TLS wrapper if needed)

---

## 2. Security Architecture

### 2.1 Three-Layer Model

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: Community String                           │
│ Purpose: Namespace isolation (like WiFi SSID)       │
│ Security: None (public identifier)                  │
│ Phase: Discovery                                    │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ Layer 2: API Key Authentication                     │
│ Purpose: Prove authorization (like WiFi password)   │
│ Security: HMAC-SHA256                               │
│ Phase: Discovery + Connection                       │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ Layer 3: Session Tokens                             │
│ Purpose: Stateless streaming                        │
│ Security: HMAC-signed, optional in data frames      │
│ Phase: Streaming                                    │
└─────────────────────────────────────────────────────┘
```

### 2.2 Security Properties

**After successful handshake:**
- Connection is authenticated (both peers verified)
- TCP connection itself proves identity
- No per-frame authentication needed
- Equivalent security to TLS session resumption

**Rationale**: Cryptographic operations are expensive. Once a TCP connection is authenticated, the connection itself (with TCP sequence numbers) is sufficient proof of identity.

---

## 3. Layer 1: Community String

### 3.1 Purpose

The community string serves as a cluster identifier, similar to:
- WiFi SSID (identifies which network)
- Kubernetes namespace (isolates workloads)
- VLAN ID (network segmentation)

### 3.2 Properties

**Public Identifier:**
- Not a secret
- Transmitted in cleartext (hashed to 8 bytes)
- Prevents accidental cluster mixing
- Does NOT provide security

**Examples:**
```python
community = "production-training-cluster"
community = "dev-experiment-42"
community = "customer-acme-inference"
```

### 3.3 Hash Function

Community strings are hashed for compactness:

```python
import hashlib

community = "my-cluster"
community_hash = hashlib.sha256(community.encode()).digest()[:8]
# Truncated to 64 bits for discovery messages
```

**Collision Probability:**
- 64-bit hash = 2^64 possible values
- Birthday paradox: 50% collision after 2^32 ≈ 4 billion clusters
- Acceptable for practical deployments

### 3.4 Security Analysis

**Attack Scenario**: Attacker guesses community string

**Mitigation**: Layer 2 (API Key) prevents unauthorized access even if community is known

**Recommendation**: Use descriptive names, not "secret" names. Security comes from API key.

---

## 4. Layer 2: API Key Authentication

### 4.1 Purpose

The API key proves a node is authorized to join the cluster. It's the primary security mechanism.

### 4.2 HMAC-Based Authentication

**Algorithm**: HMAC-SHA256

**Discovery Phase:**
```python
message = community_hash + node_uuid + port + timestamp + challenge
signature = HMAC-SHA256(api_key, message)[:16]  # Truncate to 128 bits
```

**Connection Phase (HELLO):**
```python
message = node_uuid + challenge
signature = HMAC-SHA256(api_key, message)[:16]
```

**Why HMAC?**
- Prevents rainbow table attacks
- Doesn't reveal key (unlike symmetric encryption)
- Efficient (faster than RSA signatures)
- Standard construction (RFC 2104)

### 4.3 Challenge-Response Protocol

**Purpose**: Prevent replay attacks

**Mechanism**:
1. Sender includes random 32-bit challenge
2. HMAC computed over challenge + message
3. Receiver verifies signature, records challenge
4. Old challenges (>60 seconds) rejected
5. Duplicate challenges rejected

**Example:**
```python
# Sender
challenge = secrets.randbits(32)  # Random: 0x12345678
signature = HMAC(api_key, node_id + challenge)

# Receiver
if challenge in seen_challenges:
    reject("Replay attack")
seen_challenges.add(challenge)

if not verify_hmac(api_key, received_signature):
    reject("Invalid API key")
```

### 4.4 Truncated HMAC

**Full HMAC-SHA256**: 256 bits (32 bytes)  
**Truncated**: 128 bits (16 bytes)

**Security Analysis:**
- 128 bits provides 2^64 security against birthday attacks
- Sufficient for cluster authentication (not military-grade secrets)
- Reduces overhead by 50%

**Comparison:**
| Bits | Security Level | Use Case |
|------|----------------|----------|
| 64 | Low | Not recommended |
| 96 | Medium | Acceptable |
| 128 | High | **ASoc choice** |
| 256 | Very High | Overkill for this use case |

### 4.5 API Key Requirements

**Strength:**
- Minimum 128 bits (16 bytes) entropy
- Recommended 256 bits (32 bytes)
- Use cryptographically secure random generator

**Generation:**
```python
import secrets

api_key = secrets.token_hex(32)  # 256 bits
# Example: "a3f5b8c9e2d4f7a1b6c8e9f0d3a5b7c9e1f3a5b7c9e1f3a5b7c9e1f3a5b7c9e1"
```

**Distribution:**
- Environment variables (recommended)
- Secrets manager (AWS Secrets Manager, HashiCorp Vault)
- Config file with restrictive permissions (chmod 600)
- Never hardcode in source

---

## 5. Layer 3: Session Tokens

### 5.1 Purpose

Session tokens enable stateless operation after handshake:
- Issued once during connection
- Optionally included in data frames (but not required)
- HMAC-signed to prevent forgery

### 5.2 Token Format

```
Session Token: 8 bytes (random)
Signature: 8 bytes (HMAC truncated to 64 bits)
Total: 16 bytes
```

**Generation:**
```python
session_token = secrets.token_bytes(8)  # Random 64-bit value
signature = HMAC-SHA256(api_key, session_token)[:8]
```

### 5.3 Stateless Operation

**Key Insight**: TCP connection already proves identity

After handshake:
1. Server issues session token
2. Client stores token (but doesn't need to send it)
3. Data frames have NO token overhead
4. Connection itself is proof of authentication

**Why this works:**
- TCP connections have sequence numbers (hard to hijack)
- Attacker would need to break TCP (outside our threat model)
- Equivalent to TLS session resumption without per-frame overhead

### 5.4 Optional Token Verification

Implementations MAY verify tokens on:
- First data frame only (good for long-lived connections)
- Periodically (e.g., every 1000 frames)
- Never (rely on TCP connection security)

**Reference implementation**: No verification in data frames (0.001% overhead achieved)

---

## 6. Threat Analysis

### 6.1 Threat Model

**Assumptions:**
- Nodes are not Byzantine (compromised nodes are out of scope)
- Network may be monitored (eavesdropping possible)
- API keys are pre-shared securely
- TCP implementation is secure (sequence numbers not predictable)

**Adversary Capabilities:**
- Can observe network traffic
- Can send arbitrary packets
- Cannot break HMAC-SHA256
- Cannot predict random challenges

### 6.2 Attack Scenarios

#### 6.2.1 Unauthorized Node Joining

**Attack**: Attacker tries to join cluster without API key

**Defense**:
- Discovery: HMAC signature invalid → message dropped
- Connection: HELLO signature invalid → TCP connection closed
- Result: Attacker cannot join

**Security**: Strong (depends on HMAC-SHA256 security)

#### 6.2.2 Replay Attack

**Attack**: Attacker captures and replays valid discovery/HELLO message

**Defense**:
- Each message includes random challenge
- Receiver tracks seen challenges
- Duplicate challenge → message rejected
- Old challenge (>60s) → message rejected

**Security**: Strong (2^32 challenges, short validity window)

#### 6.2.3 Man-in-the-Middle

**Attack**: Attacker intercepts and modifies messages

**Defense**:
- HMAC signature covers entire message
- Any modification invalidates signature
- Receiver rejects invalid signatures

**Security**: Strong (cannot modify without knowing API key)

**Limitation**: Attacker can DROP messages (use TLS for protection)

#### 6.2.4 Eavesdropping

**Attack**: Attacker passively observes traffic, learns tensor data

**Defense**: None in base protocol

**Mitigation**: Use TLS wrapper for confidentiality

**Rationale**: Encryption is expensive; let users opt-in via TLS if needed

#### 6.2.5 TCP Hijacking

**Attack**: Attacker hijacks authenticated TCP connection

**Defense**:
- Relies on TCP sequence number security
- Modern TCP uses random initial sequence numbers
- Attack requires predicting 32-bit sequence number

**Security**: Acceptable (TCP hijacking is hard)

**Mitigation**: Use TLS for additional protection

#### 6.2.6 Community String Guessing

**Attack**: Attacker guesses community string to join cluster

**Defense**: Layer 2 (API Key) required even if community is known

**Security**: Strong (community string is not a secret)

---

## 7. Cryptographic Algorithms

### 7.1 HMAC-SHA256

**Algorithm**: As specified in RFC 2104 and FIPS 198-1

**Key Size**: Variable (minimum 128 bits recommended)

**Output**: 256 bits (truncated to 128 bits for discovery, 64 bits for tokens)

**Implementation**: Use standard library (Python `hmac` module)

**Test Vector**:
```python
import hmac
import hashlib

key = b"test-key"
message = b"test-message"
signature = hmac.new(key, message, hashlib.sha256).digest()
# Expected: b'\xfe\x...' (32 bytes)
```

### 7.2 SHA-256 (for Community Hash)

**Algorithm**: As specified in FIPS 180-4

**Input**: UTF-8 encoded community string

**Output**: 256 bits (truncated to 64 bits)

**Collision Resistance**: 2^128 (birthday bound), sufficient for this use case

### 7.3 Random Number Generation

**Algorithm**: Use cryptographically secure PRNG

**Python**: `secrets` module (uses `os.urandom()` internally)

**Requirements**:
- Unpredictable (no observable pattern)
- Non-repeating (probability of collision negligible)

**Example**:
```python
import secrets

challenge = secrets.randbits(32)  # For challenge-response
token = secrets.token_bytes(8)     # For session tokens
api_key = secrets.token_hex(32)    # For API key generation
```

### 7.4 Timing Attack Resistance

**HMAC Comparison**: Use constant-time comparison

```python
import hmac

def verify_signature(expected, received):
    return hmac.compare_digest(expected, received)  # Constant-time
```

**Why**: Prevents timing attacks that could leak information about API key

---

## 8. Key Management

### 8.1 API Key Lifecycle

**Generation**:
```bash
# Generate 256-bit key
python -c "import secrets; print(secrets.token_hex(32))"
```

**Distribution**:
- Share via secure channel (e.g., Vault, AWS Secrets Manager)
- Use environment variables in production
- Never commit to source control

**Rotation**:
- Recommended: Monthly or after suspected compromise
- Process: 
  1. Generate new key
  2. Update all nodes
  3. Restart cluster with new key
  4. Revoke old key

**Storage**:
```bash
# Environment variable
export ASOC_API_KEY="your-key-here"

# File (restrict permissions)
echo "your-key-here" > ~/.asoc/api_key
chmod 600 ~/.asoc/api_key
```

### 8.2 Key Derivation (Future)

For large deployments, consider deriving per-cluster keys:

```python
import hashlib

master_key = b"master-secret-key"
cluster_name = "production-cluster"

cluster_key = hashlib.pbkdf2_hmac(
    'sha256',
    master_key,
    cluster_name.encode(),
    iterations=100000,
    dklen=32
)
```

This allows:
- Single master key for organization
- Derived keys per cluster
- Key revocation per cluster

### 8.3 Compromised Key Response

If API key is compromised:

1. **Immediate**: Generate new key
2. **Update**: All legitimate nodes
3. **Restart**: Cluster with new key
4. **Monitor**: For unauthorized access attempts
5. **Investigate**: How key was compromised

---

## 9. Security Considerations

### 9.1 Recommendations

**For Development:**
- Simple API keys acceptable
- Short validity windows (community string = "dev-TIMESTAMP")

**For Production:**
- Strong random API keys (256 bits)
- Network isolation (VPC, VLAN)
- Firewall rules (restrict TCP port)
- Consider TLS wrapper for sensitive data

**For Multi-Tenant:**
- Unique API key per tenant/cluster
- Network segmentation
- Rate limiting
- Monitoring and alerting

### 9.2 TLS Wrapper (Optional)

For additional security, wrap TCP connections in TLS:

```python
import ssl

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False  # If using self-signed certs
ssl_context.verify_mode = ssl.CERT_NONE  # Or use proper PKI

reader, writer = await asyncio.open_connection(
    host, port, ssl=ssl_context
)
```

**Benefits:**
- Confidentiality (encrypted tensor data)
- Perfect forward secrecy
- Mutual authentication (with client certs)

**Tradeoffs:**
- Performance overhead (~5-10%)
- Operational complexity (certificate management)

**Recommendation**: Use TLS for:
- Cross-datacenter links
- Multi-tenant environments
- Sensitive or proprietary data

### 9.3 Network Security

**Firewall Rules**:
```bash
# Allow only cluster nodes
iptables -A INPUT -p tcp --dport 9000 -s 10.0.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 9000 -j DROP

# Allow discovery within subnet only
iptables -A INPUT -p udp --dport 9999 -s 10.0.1.0/24 -j ACCEPT
iptables -A INPUT -p udp --dport 9999 -j DROP
```

**VPC/VLAN Isolation**:
- Run ASoc in private network
- No direct internet exposure
- Use VPN/private links for cross-datacenter

### 9.4 Monitoring and Alerting

**Security Events to Monitor:**
- Failed authentication attempts
- Replay attacks detected
- Unexpected nodes attempting to join
- Unusual traffic patterns

**Metrics to Track:**
- Authentication failure rate
- Connection establishment rate
- Data transfer volume per peer

**Alerting**:
```python
if auth_failure_rate > threshold:
    alert("Possible attack or misconfiguration")
```

---

## 10. Future Extensions

### 10.1 Certificate-Based Authentication

For enterprise deployments with PKI:

```
HELLO frame extension:
- Include X.509 certificate
- Server verifies certificate chain
- Mutual TLS authentication
```

**Benefits:**
- Stronger identity verification
- No shared secret management
- Per-node revocation

**Tradeoffs:**
- Operational complexity
- Certificate lifecycle management

### 10.2 Rate Limiting

Prevent DoS attacks:

```python
# Limit discovery messages per IP
if messages_from_ip > 10 per second:
    drop_message()

# Limit connection attempts per IP
if connections_from_ip > 100 per hour:
    reject_connection()
```

### 10.3 Auditing

Log security events for compliance:

```python
audit_log.write({
    "event": "authentication_success",
    "node_id": str(peer_uuid),
    "ip": peer_ip,
    "timestamp": time.time()
})
```

### 10.4 Key Rotation Protocol

Automated key rotation without cluster restart:

```
1. Server generates new key
2. Server broadcasts KEY_ROTATION control frame
3. Nodes acknowledge and switch to new key
4. Old key retained for grace period
5. Old key purged after grace period
```

---

## Appendix A: Security Checklist

**Before Deployment:**
- [ ] Generated strong API key (256 bits)
- [ ] Stored API key securely (secrets manager or environment variable)
- [ ] Configured firewall rules (restrict TCP/UDP ports)
- [ ] Network isolated (VPC/VLAN)
- [ ] Unique community string per cluster
- [ ] TLS enabled (if handling sensitive data)
- [ ] Monitoring and alerting configured

**Ongoing:**
- [ ] Rotate API keys monthly
- [ ] Monitor for authentication failures
- [ ] Review access logs weekly
- [ ] Update ASoc to latest version (security patches)

---

## Appendix B: Comparison to Alternatives

| Feature | ASoc | TLS | IPsec | SSH Tunnel |
|---------|------|-----|-------|------------|
| Handshake Size | 52 bytes | 2-4 KB | 1-2 KB | 1-2 KB |
| Per-frame Overhead | 14 bytes | 5-40 bytes | 40-80 bytes | 40+ bytes |
| CPU Overhead | <1% | 5-10% | 5-15% | 10-20% |
| Setup Complexity | Low | Medium | High | Medium |
| Confidentiality | No* | Yes | Yes | Yes |
| Use Case | AI Clusters | General | VPN | Ad-hoc |

*Add TLS wrapper if needed

---

**End of RFC-0002**

---

## Changelog

- **v0.1.0 (January 2025)**: Initial security specification

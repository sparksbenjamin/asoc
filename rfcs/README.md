# ASoc RFCs (Request for Comments)

This directory contains formal specifications for the ASoc protocol.

## Published RFCs

### [RFC-0001: Core Protocol Specification](RFC-0001-protocol.md)
**Status:** Implemented  
**Version:** 0.1.0  
**Date:** January 2025

Specifies the wire format, framing, connection semantics, and operational characteristics of ASoc. Includes:
- Discovery phase (UDP, 50-byte messages)
- Connection phase (TCP handshake, 52 bytes)
- Streaming phase (DATA frames, 14-byte headers)
- Frame format specification
- State machines
- Performance characteristics

**Key Metrics:**
- Handshake: 52 bytes (vs 450+ for JWT)
- Data overhead: 0.001%
- Throughput: 446 MB/s per peer (10 GbE)

### [RFC-0002: Security Model](RFC-0002-security.md)
**Status:** Implemented  
**Version:** 0.1.0  
**Date:** January 2025

Specifies the three-layer security architecture inspired by SNMPv3:
- Layer 1: Community strings (namespace isolation)
- Layer 2: API key authentication (HMAC-SHA256)
- Layer 3: Session tokens (stateless operation)

Includes threat analysis, cryptographic specifications, and key management best practices.

## Draft RFCs

### RFC-0003: Future Extensions (Planned)
Topics under consideration:
- RDMA transport for 100+ Gbps networks
- Compression strategies
- Hierarchical topologies for 1000+ nodes
- PyTorch/JAX integration layers
- mDNS/Avahi discovery

## RFC Process

### Proposing Changes

1. Open a GitHub Discussion in "Ideas" category
2. Describe the problem and proposed solution
3. Gather community feedback
4. Write draft RFC
5. Submit as Pull Request
6. Iterate based on review
7. Merge when consensus reached

### RFC States

- **Draft**: Under discussion, not implemented
- **Proposed**: Accepted design, implementation in progress
- **Implemented**: Shipped in reference implementation
- **Deprecated**: Replaced by newer RFC

### RFC Numbering

- **RFC-0001 to RFC-0099**: Core protocol
- **RFC-0100 to RFC-0199**: Security and authentication
- **RFC-0200 to RFC-0299**: Performance and optimizations
- **RFC-0300 to RFC-0399**: Integrations and extensions
- **RFC-0400+**: Reserved for future use

## Contributing

We welcome RFC proposals! Guidelines:

**Good RFC Topics:**
- Wire format improvements
- Security enhancements
- Performance optimizations
- New features with broad applicability

**Not RFC Topics:**
- Bug fixes (use GitHub Issues)
- Implementation details (use code comments)
- Application-specific features

**RFC Template:**
```markdown
# RFC-NNNN: Title

**Status:** Draft  
**Version:** 0.0.1  
**Date:** Month Year  
**Author:** Your Name  

## Abstract
Brief summary (2-3 sentences)

## Motivation
Why is this change needed?

## Specification
Detailed technical specification

## Security Considerations
Impact on security model

## Performance Impact
Benchmarks or analysis

## Backward Compatibility
How this affects existing deployments

## References
Related RFCs, papers, implementations
```

## Questions?

- **Technical questions**: Open GitHub Issue
- **Design discussions**: GitHub Discussions
- **General questions**: See main README

## References

ASoc is inspired by:
- **WebSocket (RFC 6455)**: Simple framing
- **HTTP/2 (RFC 7540)**: Binary protocol design
- **QUIC (RFC 9000)**: Stream multiplexing
- **SNMPv3 (RFC 3414)**: Security model
- **NCCL**: Tensor-aware collective operations

---

**Want to implement ASoc in another language?** These RFCs are your specification. Follow RFC-0001 for wire format compatibility.

"""
ASoc - AI Socket Protocol

Ultra-compact, peer-to-peer, tensor-native networking for AI workloads.
"""

__version__ = "0.1.0"
__author__ = "ASoc Contributors"
__license__ = "MIT"

from .node_ready import NodeReady
from .protocol_binary import (
    encode_frame,
    decode_header,
    encode_hello,
    decode_hello,
    encode_accept,
    decode_accept,
    uuid_to_bytes,
    bytes_to_uuid,
)
from .discovery_binary import BinaryDiscovery

__all__ = [
    "NodeReady",
    "BinaryDiscovery",
    "encode_frame",
    "decode_header",
    "encode_hello",
    "decode_hello",
    "encode_accept",
    "decode_accept",
    "uuid_to_bytes",
    "bytes_to_uuid",
]

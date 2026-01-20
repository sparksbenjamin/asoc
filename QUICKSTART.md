# ASoc Quick Start

## 1. Get the Code

```bash
# Download and unzip
unzip asoc-protocol-github.zip
cd asoc-protocol
```

## 2. Test It Works

```bash
python test_setup.py
```

## 3. Run Benchmark

```bash
python benchmark_ready.py
```

## 4. Try the Examples

```bash
# Simple example with auto-discovery
python examples/simple.py

# Static configuration (for firewalls/VLANs)
python examples/static_peers.py
```

## 5. Use in Your Code

```python
import asyncio
from asoc import NodeReady

async def main():
    # Create and start node
    node = NodeReady(
        community="my-cluster",
        api_key="secret-key"
    )
    await node.start()
    await asyncio.sleep(3)
    
    # Stream tensor to peer
    peers = node.get_peer_ids()
    if peers:
        data = b"your tensor bytes..."
        await node.stream_tensor(peers[0], data)
    
    await node.shutdown()

asyncio.run(main())
```

## 6. Deploy to Production

See `INSTALL.md` and `docs/deployment.md` for:
- Docker/Kubernetes
- Static configuration
- Environment variables
- Security best practices

## Common Commands

```bash
# Install as package (optional)
pip install -e .

# Run test
python test_setup.py

# Run benchmark
python benchmark_ready.py

# Run examples
python examples/simple.py
python examples/static_peers.py
```

## File Structure

```
asoc-protocol/
├── asoc/               # Core protocol library
│   ├── __init__.py
│   ├── protocol_binary.py
│   ├── discovery_binary.py
│   └── node_ready.py
├── examples/           # Usage examples
├── docs/              # Documentation
├── test_setup.py      # Verify setup
└── benchmark_ready.py # Performance test
```

## Need Help?

- **Documentation**: Read `README.md`
- **Installation**: See `INSTALL.md`
- **Deployment**: Check `docs/deployment.md`
- **Contributing**: See `CONTRIBUTING.md`

## Quick Reference

**Create node:**
```python
node = NodeReady(community="cluster", api_key="key")
```

**Start node:**
```python
await node.start()
```

**Send data:**
```python
await node.stream_tensor(peer_id, data)
```

**Static peers:**
```python
node = NodeReady(
    community="cluster",
    api_key="key",
    static_peers=["10.0.1.10:9000"],
    enable_discovery=False
)
```

**That's it!** 🚀

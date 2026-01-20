# Installation Guide

## Quick Install (No pip)

ASoc has zero dependencies. Just clone and run:

```bash
git clone https://github.com/yourusername/asoc-protocol.git
cd asoc-protocol
python test_setup.py
```

## Install via pip (Optional)

```bash
pip install -e .
```

This makes ASoc importable from anywhere and adds command-line tools:
- `asoc-test` - Run tests
- `asoc-benchmark` - Run benchmarks

## Requirements

- Python 3.7 or higher
- That's it!

Optional:
- `numpy` for benchmark data generation (will use Python's random if not available)

## Verify Installation

```bash
python test_setup.py
```

Expected output:
```
✓ Python version OK
✓ asoc.NodeReady imported
✓ asoc.protocol imported
✓ asoc.discovery imported
✅ ALL TESTS PASSED
```

## Platform Support

Tested on:
- Linux (Ubuntu, Debian, RHEL, Arch)
- macOS (10.14+)
- Windows (10, 11)

## Network Requirements

For UDP discovery:
- Outbound: UDP port 9999 (broadcast)
- Inbound: TCP port 9000 (default, configurable)

For static configuration:
- Only TCP port 9000 (or your configured port)

## Firewall Configuration

### Linux (UFW)
```bash
sudo ufw allow 9000/tcp
sudo ufw allow 9999/udp
```

### Linux (iptables)
```bash
sudo iptables -A INPUT -p tcp --dport 9000 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 9999 -j ACCEPT
```

### macOS
```bash
# Firewall usually allows localhost by default
# For production, configure via System Preferences > Security
```

### Windows
```powershell
New-NetFirewallRule -DisplayName "ASoc TCP" -Direction Inbound -Protocol TCP -LocalPort 9000 -Action Allow
New-NetFirewallRule -DisplayName "ASoc UDP" -Direction Inbound -Protocol UDP -LocalPort 9999 -Action Allow
```

## Docker

```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
CMD ["python", "test_setup.py"]
```

```bash
docker build -t asoc .
docker run asoc
```

## Troubleshooting

### Import errors
Make sure you're in the correct directory or have installed via pip.

### Nodes not connecting
1. Check firewall settings
2. Try static configuration instead of discovery
3. Verify both nodes have same community and API key

### Port already in use
Change the port:
```python
node = NodeReady(..., port=9100)
```

## Next Steps

- Run examples: `python examples/simple.py`
- Read documentation: `docs/`
- Join discussions: GitHub Discussions

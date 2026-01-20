# ASoc Production Deployment Guide

## Discovery vs Static Configuration

### When to Use Discovery (UDP Broadcast)
✅ **Development/Testing**
- Single subnet
- Local network
- Quick prototyping
- No firewall restrictions

### When to Use Static Configuration
✅ **Production Environments**
- VLANs
- Firewalls blocking UDP
- Cloud deployments (AWS, GCP, Azure)
- Kubernetes clusters
- Cross-datacenter
- Corporate networks
- Any scenario where broadcast doesn't work

---

## Static Configuration Methods

### 1. Hardcoded Peers (Simple)

```python
from static_config import StaticNode

node = StaticNode(
    community="production-cluster",
    api_key="your-secret-key",
    static_peers=[
        "10.0.1.10:9000",
        "10.0.2.20:9000",
        "10.0.3.30:9000"
    ],
    port=9000
)

await node.start()
```

### 2. Environment Variables (12-Factor App)

```bash
# Set environment variable
export ASOC_COMMUNITY="production-cluster"
export ASOC_API_KEY="your-secret-key"
export ASOC_PEERS="10.0.1.10:9000,10.0.2.20:9000,10.0.3.30:9000"
export ASOC_PORT="9000"
```

```python
import os
from static_config import StaticNode, load_peers_from_env

node = StaticNode(
    community=os.environ["ASOC_COMMUNITY"],
    api_key=os.environ["ASOC_API_KEY"],
    static_peers=load_peers_from_env("ASOC_PEERS"),
    port=int(os.environ.get("ASOC_PORT", "9000"))
)

await node.start()
```

### 3. Configuration File (Operations-Friendly)

**`/etc/asoc/config.ini`**
```ini
[asoc]
community = production-cluster
api_key = your-secret-key
port = 9000

[peers]
# One peer per line
peer1 = 10.0.1.10:9000
peer2 = 10.0.2.20:9000
peer3 = 10.0.3.30:9000
```

**`/etc/asoc/peers.conf`** (simpler format)
```
# ASoc peer list
# One peer per line, comments allowed

10.0.1.10:9000
10.0.2.20:9000
10.0.3.30:9000

# More peers can be added dynamically
```

```python
import configparser
from static_config import StaticNode, load_peers_from_file

# Load config
config = configparser.ConfigParser()
config.read('/etc/asoc/config.ini')

node = StaticNode(
    community=config['asoc']['community'],
    api_key=config['asoc']['api_key'],
    static_peers=load_peers_from_file('/etc/asoc/peers.conf'),
    port=int(config['asoc']['port'])
)

await node.start()
```

### 4. Hybrid Mode (Static Seed + Discovery)

Use static peers as "seed nodes" and discover others:

```python
node = StaticNode(
    community="hybrid-cluster",
    api_key="secret-key",
    static_peers=[
        "seed1.example.com:9000",  # Always reachable seed node
        "seed2.example.com:9000"
    ],
    enable_discovery=True,  # Also use UDP discovery for local peers
    port=9000
)
```

**Use case:** Multi-datacenter where each DC has discovery, but DCs connect via static seeds.

---

## Deployment Scenarios

### Docker Compose

**`docker-compose.yml`**
```yaml
version: '3.8'

services:
  asoc-node1:
    image: asoc:latest
    environment:
      ASOC_COMMUNITY: prod-cluster
      ASOC_API_KEY: ${ASOC_API_KEY}
      ASOC_PEERS: asoc-node2:9000,asoc-node3:9000
      ASOC_PORT: 9000
    ports:
      - "9001:9000"
    networks:
      - asoc-net

  asoc-node2:
    image: asoc:latest
    environment:
      ASOC_COMMUNITY: prod-cluster
      ASOC_API_KEY: ${ASOC_API_KEY}
      ASOC_PEERS: asoc-node1:9000,asoc-node3:9000
      ASOC_PORT: 9000
    ports:
      - "9002:9000"
    networks:
      - asoc-net

  asoc-node3:
    image: asoc:latest
    environment:
      ASOC_COMMUNITY: prod-cluster
      ASOC_API_KEY: ${ASOC_API_KEY}
      ASOC_PEERS: asoc-node1:9000,asoc-node2:9000
      ASOC_PORT: 9000
    ports:
      - "9003:9000"
    networks:
      - asoc-net

networks:
  asoc-net:
    driver: bridge
```

**`.env`**
```
ASOC_API_KEY=your-secret-key-here
```

### Kubernetes

**`asoc-configmap.yaml`**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: asoc-config
  namespace: ml-training
data:
  peers.conf: |
    asoc-node-0.asoc-headless.ml-training.svc.cluster.local:9000
    asoc-node-1.asoc-headless.ml-training.svc.cluster.local:9000
    asoc-node-2.asoc-headless.ml-training.svc.cluster.local:9000
```

**`asoc-secret.yaml`**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: asoc-secret
  namespace: ml-training
type: Opaque
stringData:
  api-key: "your-secret-key-here"
  community: "k8s-training-cluster"
```

**`asoc-statefulset.yaml`**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: asoc-headless
  namespace: ml-training
spec:
  clusterIP: None
  selector:
    app: asoc-node
  ports:
  - port: 9000
    name: asoc

---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: asoc-node
  namespace: ml-training
spec:
  serviceName: asoc-headless
  replicas: 3
  selector:
    matchLabels:
      app: asoc-node
  template:
    metadata:
      labels:
        app: asoc-node
    spec:
      containers:
      - name: asoc
        image: asoc:latest
        ports:
        - containerPort: 9000
          name: asoc
        env:
        - name: ASOC_COMMUNITY
          valueFrom:
            secretKeyRef:
              name: asoc-secret
              key: community
        - name: ASOC_API_KEY
          valueFrom:
            secretKeyRef:
              name: asoc-secret
              key: api-key
        - name: ASOC_PORT
          value: "9000"
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        volumeMounts:
        - name: config
          mountPath: /etc/asoc
      volumes:
      - name: config
        configMap:
          name: asoc-config
```

### AWS (Terraform)

**`main.tf`**
```hcl
resource "aws_security_group" "asoc" {
  name        = "asoc-cluster"
  description = "ASoc peer-to-peer communication"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 9000
    to_port     = 9000
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "asoc_node" {
  count         = 3
  ami           = var.ami_id
  instance_type = "p3.2xlarge"  # GPU instance
  
  vpc_security_group_ids = [aws_security_group.asoc.id]
  subnet_id              = var.subnet_id
  
  user_data = templatefile("${path.module}/user-data.sh", {
    community = var.asoc_community
    api_key   = var.asoc_api_key
    peers     = join(",", [for i in range(3) : "10.0.1.${10 + i}:9000"])
  })
  
  tags = {
    Name = "asoc-node-${count.index}"
  }
}
```

**`user-data.sh`**
```bash
#!/bin/bash

# Install ASoc
pip install asoc

# Configure
cat > /etc/asoc/config.py << EOF
import os
from static_config import StaticNode

node = StaticNode(
    community="${community}",
    api_key="${api_key}",
    static_peers="${peers}".split(","),
    port=9000
)
EOF

# Run as systemd service
systemctl enable asoc
systemctl start asoc
```

---

## DNS-Based Discovery (Advanced)

For large clusters, use DNS SRV records:

**DNS Configuration:**
```
_asoc._tcp.cluster.example.com. 86400 IN SRV 10 60 9000 node1.cluster.example.com.
_asoc._tcp.cluster.example.com. 86400 IN SRV 10 20 9000 node2.cluster.example.com.
_asoc._tcp.cluster.example.com. 86400 IN SRV 10 20 9000 node3.cluster.example.com.
```

**Python Code:**
```python
import socket

def discover_peers_from_dns(service_name="_asoc._tcp.cluster.example.com"):
    """Discover peers via DNS SRV records"""
    try:
        answers = socket.getaddrinfo(
            service_name, 
            None, 
            socket.AF_INET, 
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP
        )
        
        peers = []
        for answer in answers:
            host = answer[4][0]
            # SRV records contain port, but getaddrinfo doesn't return it
            # Would need dnspython for full SRV support
            peers.append(f"{host}:9000")
        
        return peers
    except Exception as e:
        print(f"DNS discovery failed: {e}")
        return []

# Use it
node = StaticNode(
    community="dns-cluster",
    api_key="secret",
    static_peers=discover_peers_from_dns(),
    port=9000
)
```

---

## Security Best Practices

### 1. API Key Management

**❌ Don't:**
```python
node = StaticNode(api_key="hardcoded-secret")  # NEVER!
```

**✅ Do:**
```python
import os
import secrets

# Use environment variables
api_key = os.environ.get("ASOC_API_KEY")

# Or secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
from aws_secretsmanager import get_secret
api_key = get_secret("prod/asoc/api-key")

# Generate secure keys
secure_key = secrets.token_hex(32)  # 256-bit key
```

### 2. Network Isolation

- Use VPC/VNet for isolation
- Security groups/firewall rules: only allow port 9000 from cluster CIDR
- Consider VPN or private links for cross-datacenter

### 3. TLS Wrapper (Optional)

For encrypted transport:

```python
import ssl

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain('cert.pem', 'key.pem')

# Wrap connections with TLS (future feature)
node = StaticNode(
    community="secure-cluster",
    api_key="secret",
    static_peers=["10.0.1.10:9000"],
    ssl_context=ssl_context  # TODO: implement
)
```

---

## Monitoring & Operations

### Health Check Endpoint

```python
from aiohttp import web

async def health_check(request):
    """HTTP health check for load balancers"""
    peers = len(node.peers)
    return web.json_response({
        "status": "healthy" if peers > 0 else "degraded",
        "peers": peers,
        "node_id": node.node_id
    })

app = web.Application()
app.router.add_get('/health', health_check)
web.run_app(app, host='0.0.0.0', port=8080)
```

### Metrics

```python
# Prometheus metrics (example)
from prometheus_client import Counter, Gauge, Histogram

bytes_sent = Counter('asoc_bytes_sent_total', 'Total bytes sent')
bytes_recv = Counter('asoc_bytes_recv_total', 'Total bytes received')
active_peers = Gauge('asoc_active_peers', 'Number of active peers')
transfer_duration = Histogram('asoc_transfer_duration_seconds', 'Transfer duration')
```

---

## Troubleshooting

### Peers Not Connecting

```bash
# Check if port is accessible
telnet 10.0.1.10 9000

# Check firewall rules
sudo iptables -L -n | grep 9000

# Check if node is listening
sudo netstat -tlnp | grep 9000
```

### Authentication Failures

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check API key matches
print(f"API key hash: {hashlib.sha256(api_key.encode()).hexdigest()}")
```

### Performance Issues

```python
# Check connection stats
stats = await node.get_connection_stats()
print(f"RTT: {stats['rtt_ms']}ms")
print(f"Throughput: {stats['mbps']}MB/s")
```

---

## Summary

**Development:** Use discovery (UDP broadcast) for quick setup

**Production:** Use static configuration with:
- Environment variables (cloud-native)
- Configuration files (traditional ops)
- DNS SRV records (large scale)
- Hybrid mode (best of both)

**Key principle:** Static configuration gives you full control and works everywhere.

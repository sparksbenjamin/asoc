# Running ASoc on SLURM HPC Clusters

## Quick Start

```bash
# 1. Copy ASoc to your HPC home directory
scp -r asoc-protocol user@hpc.university.edu:~/

# 2. SSH to HPC
ssh user@hpc.university.edu

# 3. Submit job
cd ~/asoc-protocol/slurm
sbatch asoc_benchmark.slurm
```

## Files Needed

```
slurm/
├── asoc_benchmark.slurm   # SLURM job script
├── slurm_benchmark.py     # Benchmark code
└── README_SLURM.md        # This file
```

## SLURM Job Script Explained

### Basic Configuration

```bash
#SBATCH --nodes=4              # Number of compute nodes
#SBATCH --ntasks-per-node=1    # One ASoc process per node
#SBATCH --time=00:30:00        # 30 minutes max
#SBATCH --partition=gpu        # Which partition/queue
```

### Key Concepts

**Why static peers?**
- HPC compute nodes usually can't do UDP broadcast
- Network topology varies (InfiniBand, Omni-Path, Ethernet)
- Firewalls between compute nodes
- Static configuration is more reliable

**How it works:**
1. SLURM allocates nodes
2. Script builds peer list from `$SLURM_JOB_NODELIST`
3. Each node connects to all others via TCP
4. Rank 0 broadcasts tensors to all other ranks

## Customization for Your HPC

### 1. Module Names

Edit `asoc_benchmark.slurm`:

```bash
# Replace with your cluster's modules
module load python/3.11      # Your Python version
module load cuda/12.0        # If using GPUs
module load openmpi/4.1      # If needed
```

Find available modules:
```bash
module avail
module spider python
```

### 2. Partition Names

```bash
# Find your cluster's partitions
sinfo

# Common names: compute, gpu, bigmem, debug, long
#SBATCH --partition=compute  # Use your partition name
```

### 3. Network Interface

If your HPC has multiple network interfaces (e.g., InfiniBand + Ethernet):

```bash
# In asoc_benchmark.slurm, before running:
export ASOC_INTERFACE="ib0"  # Use InfiniBand
# or
export ASOC_INTERFACE="eth0"  # Use Ethernet
```

Then modify `slurm_benchmark.py` to use specific interface:

```python
# Get IP of specific interface
import netiface
ip = netiface.ifaddresses('ib0')[netiface.AF_INET][0]['addr']
```

### 4. Shared vs Local Filesystem

**Shared filesystem (most common):**
```bash
# Code is accessible from all nodes
cd ~/asoc-protocol
sbatch slurm/asoc_benchmark.slurm
```

**Local scratch (faster but requires copying):**
```bash
# In SLURM script, add:
LOCAL_SCRATCH="/tmp/$SLURM_JOB_ID"
srun --nodes=$SLURM_JOB_NUM_NODES mkdir -p $LOCAL_SCRATCH
srun --nodes=$SLURM_JOB_NUM_NODES cp -r ~/asoc-protocol $LOCAL_SCRATCH/
cd $LOCAL_SCRATCH/asoc-protocol
```

## Common HPC Scenarios

### Scenario 1: GPU Cluster (Multi-Node Training)

```bash
#!/bin/bash
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:4           # 4 GPUs per node
#SBATCH --partition=gpu
#SBATCH --time=02:00:00

module load cuda/12.0
module load python/3.11

# Set GPU-specific environment
export CUDA_VISIBLE_DEVICES=0,1,2,3

# Run benchmark
srun python slurm_benchmark.py \
     --rank $SLURM_PROCID \
     --world-size $SLURM_JOB_NUM_NODES \
     --tensor-size-mb 1000        # 1GB tensors
```

### Scenario 2: InfiniBand Network

```bash
#!/bin/bash
#SBATCH --nodes=8
#SBATCH --partition=ib          # InfiniBand partition

# Use InfiniBand interface
export ASOC_PORT=9000

# Build peer list using IB addresses
PEER_LIST=""
for node in $(scontrol show hostnames $SLURM_JOB_NODELIST); do
    IB_ADDR=$(ssh $node "ip addr show ib0 | grep 'inet ' | awk '{print \$2}' | cut -d/ -f1")
    PEER_LIST="${PEER_LIST}${IB_ADDR}:9000,"
done
export ASOC_PEERS="${PEER_LIST%,}"  # Remove trailing comma

srun python slurm_benchmark.py ...
```

### Scenario 3: Large Scale (100+ nodes)

```bash
#!/bin/bash
#SBATCH --nodes=128
#SBATCH --time=04:00:00

# Use hierarchical connection strategy
# Each node connects to neighbors only, not all-to-all
# Modify slurm_benchmark.py to build ring topology

# Increase connection timeout
export ASOC_CONNECTION_TIMEOUT=120  # 2 minutes

srun python slurm_benchmark.py ...
```

### Scenario 4: Job Array (Multiple Independent Runs)

```bash
#!/bin/bash
#SBATCH --array=1-10           # 10 independent runs
#SBATCH --nodes=4

# Each array task gets different community
export ASOC_COMMUNITY="benchmark-run-${SLURM_ARRAY_TASK_ID}"

srun python slurm_benchmark.py ...
```

## Monitoring & Debugging

### Check Job Status

```bash
# View queue
squeue -u $USER

# Watch job
watch -n 1 'squeue -u $USER'

# Check job details
scontrol show job <JOBID>
```

### View Output

```bash
# While running
tail -f asoc_<JOBID>.out

# After completion
cat asoc_<JOBID>.out
cat asoc_<JOBID>.err
```

### Debug Connection Issues

```bash
# Test node connectivity
srun --nodes=2 --ntasks=2 hostname

# Test port availability
srun --nodes=2 --ntasks=2 netstat -tlnp | grep 9000

# Test TCP connection between nodes
srun --nodes=2 --ntasks=2 bash -c '
  if [ $SLURM_PROCID -eq 0 ]; then
    python -m http.server 9000 &
    sleep 2
  else
    curl http://$(scontrol show hostnames $SLURM_JOB_NODELIST | head -1):9000
  fi
'
```

### Common Issues

**Problem: "No peers connected"**
```bash
# Solution 1: Check firewall
srun iptables -L | grep 9000

# Solution 2: Try different port
export ASOC_PORT=12345

# Solution 3: Check node hostnames resolve
srun --nodes=2 --ntasks=2 bash -c 'ping -c 1 $(hostname)'
```

**Problem: "Address already in use"**
```bash
# Solution: Use job ID in port number
export ASOC_PORT=$((9000 + $SLURM_JOB_ID % 1000))
```

**Problem: Slow connection setup**
```bash
# Solution: Increase timeout in slurm_benchmark.py
connection_timeout = 120  # 2 minutes for large clusters
```

## Performance Tips

### 1. Use Fast Network

```bash
# Prefer InfiniBand over Ethernet
#SBATCH --constraint=ib

# Or specify network explicitly
module load infiniband
```

### 2. Disable Discovery

Always use static peers in HPC:
```python
node = NodeReady(
    enable_discovery=False,  # Always False for HPC!
    static_peers=peer_list
)
```

### 3. Tune Chunk Size

```python
# Larger chunks for high-bandwidth networks
await node.stream_tensor(
    peer_id, 
    data, 
    chunk_size=10*1024*1024  # 10MB chunks for InfiniBand
)
```

### 4. CPU Pinning

```bash
#SBATCH --cpus-per-task=4

# In script:
export OMP_NUM_THREADS=4
export OMP_PLACES=cores
export OMP_PROC_BIND=close
```

## Benchmarking Strategy

### Full Mesh (All-to-All)

```bash
# Every node sends to every other node
# Good for: testing maximum aggregate bandwidth
sbatch asoc_benchmark.slurm --nodes=4
```

### Ring Topology

```bash
# Each node sends to next in ring
# Good for: large scale, lower connection overhead
# Modify slurm_benchmark.py to implement ring
```

### Parameter Sweep

```bash
# Test different tensor sizes
for size in 10 100 1000; do
    sbatch asoc_benchmark.slurm \
           --export=TENSOR_SIZE=$size
done
```

## Example Output

```
==============================================
ASoc SLURM Benchmark - Rank 0/4
==============================================
Node: node001
Connected to 3 peers

Iteration 1/5
  Elapsed: 1.23s
  Total data: 300MB (100MB × 3 peers)
  Aggregate throughput: 243.9 MB/s
  Per-peer throughput: 81.3 MB/s

...

BENCHMARK SUMMARY
==============================================
World size: 4 nodes
Tensor size: 100MB
Average aggregate throughput: 245.2 MB/s
Protocol overhead: 0.001%
==============================================
```

## Comparing to Other Systems

### vs MPI

```bash
# ASoc
sbatch asoc_benchmark.slurm

# MPI (for comparison)
sbatch mpi_benchmark.slurm
```

### vs NCCL

```bash
# ASoc works across any GPUs
# NCCL requires NVIDIA + proper topology
```

## Production Deployment

For long-running jobs:

```bash
#!/bin/bash
#SBATCH --nodes=16
#SBATCH --time=48:00:00        # 2 days
#SBATCH --partition=long
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=you@email.com

# Checkpointing
export ASOC_CHECKPOINT_DIR=/scratch/$USER/checkpoints

# Restart on failure
#SBATCH --requeue

# Resource reservations
#SBATCH --reservation=my-reservation
```

## Next Steps

1. Run test job: `sbatch asoc_benchmark.slurm`
2. Check output: `tail -f asoc_*.out`
3. Tune parameters for your cluster
4. Integrate with your training code
5. Compare against MPI/NCCL benchmarks

## Support

- Check SLURM docs: `man sbatch`
- HPC support: Contact your cluster admins
- ASoc issues: GitHub Issues

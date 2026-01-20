# ASoc SLURM Quick Reference

## TL;DR - Run Benchmark on HPC

```bash
# 1. Copy to HPC
scp -r asoc-protocol/ user@hpc:~/

# 2. SSH and submit
ssh user@hpc
cd ~/asoc-protocol/slurm
sbatch asoc_benchmark.slurm

# 3. Watch output
tail -f asoc_*.out
```

## Files

```
slurm/
├── asoc_benchmark.slurm    # SLURM job script (submit this)
├── slurm_benchmark.py      # Python benchmark code
└── README_SLURM.md         # Full documentation
```

## Customize for Your Cluster

### Edit `asoc_benchmark.slurm`:

```bash
# Line 4: Number of nodes
#SBATCH --nodes=4              # Change to your needs

# Line 7: Time limit
#SBATCH --time=00:30:00        # Adjust as needed

# Line 8: Partition name
#SBATCH --partition=compute    # Use: sinfo to see available

# Lines 25-26: Module names
module load python/3.11        # Your Python module
```

### Key Concepts

**Static Peers (Not Discovery)**
- HPC networks don't allow UDP broadcast
- Script builds peer list from allocated nodes
- Each node connects to all others via TCP

**How It Works:**
1. SLURM allocates N nodes
2. Script gets node hostnames from `$SLURM_JOB_NODELIST`
3. Builds peer list: `node1:9000,node2:9000,...`
4. Each node runs `slurm_benchmark.py` simultaneously
5. Nodes connect via static peers
6. Rank 0 broadcasts to all, others receive

## Common Cluster Types

### Standard CPU Cluster
```bash
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --partition=compute
```

### GPU Cluster
```bash
#SBATCH --nodes=4
#SBATCH --gres=gpu:4           # 4 GPUs per node
#SBATCH --partition=gpu
```

### InfiniBand Network
```bash
#SBATCH --constraint=ib        # Request IB nodes
#SBATCH --ntasks-per-node=1
```

## Submit & Monitor

```bash
# Submit job
sbatch asoc_benchmark.slurm

# Check status
squeue -u $USER

# Watch output (replace JOBID)
tail -f asoc_12345.out

# Cancel job
scancel <JOBID>
```

## Expected Output

```
==============================================
ASoc SLURM Benchmark - Rank 0/4
==============================================
Connected to 3 peers

Iteration 1/5
  Elapsed: 1.23s
  Total data: 300MB
  Aggregate throughput: 243.9 MB/s

BENCHMARK SUMMARY
Average aggregate throughput: 245.2 MB/s
Protocol overhead: 0.001%
==============================================
```

## Troubleshooting

### No peers connected?
```bash
# Check node connectivity
srun --nodes=2 --ntasks=2 hostname

# Try different port
export ASOC_PORT=12345
```

### Module not found?
```bash
# Find available modules
module avail python
module spider python

# Use version-specific module
module load python/3.11.5
```

### Port already in use?
```bash
# Add to asoc_benchmark.slurm:
export ASOC_PORT=$((9000 + $SLURM_JOB_ID % 1000))
```

## Performance Tips

1. **Use fast network**: InfiniBand > Omni-Path > Ethernet
2. **Disable discovery**: Always use static peers in HPC
3. **Tune chunk size**: Larger chunks for high-bandwidth networks
4. **Request IB nodes**: `#SBATCH --constraint=ib`

## Next Steps

1. Customize `asoc_benchmark.slurm` for your cluster
2. Submit: `sbatch asoc_benchmark.slurm`
3. Monitor: `tail -f asoc_*.out`
4. Compare to MPI/NCCL benchmarks
5. Integrate with your training pipeline

## Full Documentation

See `README_SLURM.md` for:
- Detailed configuration
- Multiple scenarios (GPU, IB, large scale)
- Debugging guide
- Production deployment

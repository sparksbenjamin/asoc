#!/bin/bash
#SBATCH --job-name=asoc-benchmark
#SBATCH --nodes=2                    # Number of nodes
#SBATCH --ntasks-per-node=1          # One process per node
#SBATCH --cpus-per-task=4            # CPUs per task
#SBATCH --time=00:30:00              # 30 minutes
#SBATCH --partition=gpu              # GPU partition (adjust for your cluster)
#SBATCH --gres=gpu:1                 # 1 GPU per node (optional)
#SBATCH --output=asoc_%j.out         # Output file
#SBATCH --error=asoc_%j.err          # Error file

# ASoc Benchmark on SLURM
# This script runs ASoc across multiple HPC nodes using static configuration

set -e

echo "=============================================="
echo "ASoc SLURM Benchmark"
echo "=============================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Nodes: $SLURM_JOB_NUM_NODES"
echo "Node list: $SLURM_JOB_NODELIST"
echo "=============================================="

# Load modules (adjust for your HPC)
module purge
module load python/3.11  # Or your Python module

# Optional: Load CUDA if using GPUs
# module load cuda/12.0

# Create virtual environment (if not already done)
if [ ! -d "$HOME/asoc-venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv $HOME/asoc-venv
    source $HOME/asoc-venv/bin/activate
    pip install --upgrade pip
    pip install numpy  # For benchmark
else
    source $HOME/asoc-venv/bin/activate
fi

# Get node hostnames
NODES=($(scontrol show hostnames $SLURM_JOB_NODELIST))
echo "Nodes allocated: ${NODES[@]}"

# Use first node as rank 0 (sender), rest as receivers
RANK0_NODE=${NODES[0]}
echo "Rank 0 (sender): $RANK0_NODE"

# Configuration
export ASOC_COMMUNITY="slurm-benchmark-$SLURM_JOB_ID"
export ASOC_API_KEY="slurm-secret-$(date +%s)"
export ASOC_PORT=9000

# Create peer list (all nodes)
PEER_LIST=""
for node in "${NODES[@]}"; do
    if [ -z "$PEER_LIST" ]; then
        PEER_LIST="${node}:${ASOC_PORT}"
    else
        PEER_LIST="${PEER_LIST},${node}:${ASOC_PORT}"
    fi
done
export ASOC_PEERS="$PEER_LIST"

echo "Peer list: $ASOC_PEERS"
echo "=============================================="

# Copy ASoc code to compute nodes (if not on shared filesystem)
# srun --nodes=$SLURM_JOB_NUM_NODES cp -r ~/asoc-protocol /tmp/

# Run the benchmark script on all nodes simultaneously
# Each node will connect to others via static peer configuration
srun --nodes=$SLURM_JOB_NUM_NODES \
     --ntasks=$SLURM_JOB_NUM_NODES \
     --ntasks-per-node=1 \
     python slurm_benchmark.py \
     --rank $SLURM_PROCID \
     --world-size $SLURM_JOB_NUM_NODES \
     --node-name $(hostname)

echo "=============================================="
echo "Benchmark complete!"
echo "Results saved to asoc_${SLURM_JOB_ID}.out"
echo "=============================================="

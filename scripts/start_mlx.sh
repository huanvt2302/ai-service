#!/bin/bash
set -e

echo "═════════════════════════════════════════════════════════════"
echo "  Starting Native MLX Inference Server (Apple Silicon GPU)"
echo "═════════════════════════════════════════════════════════════"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 could not be found. Please install Python 3.11 or newer."
    exit 1
fi

VENV_DIR=".venv_mlx"

if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating Python virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "[*] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "[*] Installing/Upgrading MLX packages..."
pip install --upgrade pip
pip install --upgrade mlx-lm mlx-vlm

# Load environment variables from .env if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Set the HF_TOKEN directly if not found in .env
if [ -z "$HF_TOKEN" ]; then
    export HF_TOKEN="xxxxx"
fi

# Qwen3.5-4B-MLX-4bit is recommended to be run in 4-bit for efficiency
MODEL="mlx-community/Qwen3-VL-4B-Instruct-4bit"

echo ""
echo "[*] Starting mlx_lm.server with model: $MODEL"
echo "[*] The server will listen on http://0.0.0.0:9999"
echo "[*] (This allows requests from the Docker backend via host.docker.internal)"
echo "[*] Press Ctrl+C to stop."
echo "-------------------------------------------------------------"

# Start the server (OpenAI-compatible wrapper from mlx-lm)
mlx_lm.server --model "$MODEL" --port 9999 --host 0.0.0.0

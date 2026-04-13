#!/usr/bin/env python3
"""
Init script: download GGUF model from HuggingFace if not already cached.
Runs once as a Docker init container before llama-cpp starts.
"""
import os
import shutil
import sys


def main():
    model_file = os.getenv("LLAMA_CPP_MODEL", "qwen2.5-3b-instruct-q4_k_m.gguf")
    dest = f"/models/{model_file}"

    if os.path.exists(dest):
        print(f"[model-downloader] Model already exists at {dest}, skipping download.")
        sys.exit(0)

    print(f"[model-downloader] Downloading {model_file} ...")

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[model-downloader] Installing huggingface_hub ...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"])
        from huggingface_hub import hf_hub_download

    token = os.getenv("HF_TOKEN") or None
    repo_id = os.getenv("HF_REPO_ID", "Qwen/Qwen2.5-3B-Instruct-GGUF")

    print(f"[model-downloader] Fetching from repo: {repo_id}, file: {model_file}")
    cached_path = hf_hub_download(
        repo_id=repo_id,
        filename=model_file,
        token=token,
    )
    shutil.copy(cached_path, dest)
    print(f"[model-downloader] Model saved to {dest}")


if __name__ == "__main__":
    main()

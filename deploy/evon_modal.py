"""Serve Gnani Evon (gnani/gnani-evon-v3.3-30B-A3B) as an OpenAI-compatible API on Modal.

Evon is 30B parameters in BF16 (~60 GB of weights), so it needs an 80 GB GPU
(H100/A100-80GB). A laptop cannot run it; Modal gives new accounts free monthly
credit, enough for development and recording the demo.

    pip install modal && modal setup
    modal secret create evon-key EVON_API_KEY=<pick-a-long-random-string>
    modal deploy deploy/evon_modal.py

Then put in bahi-khata/.env:
    EVON_BASE_URL=https://<your-workspace>--bolda-khata-evon-serve.modal.run/v1
    EVON_API_KEY=<same string>

The first request after idle cold-starts the GPU (a few minutes the very first
time while weights download; faster afterwards thanks to the cache volume). The
app keeps working on its on-device model whenever Evon is unavailable.
NOTE: written against vLLM's documented CLI; not yet run end-to-end from this repo.
"""
import os
import subprocess

import modal

MODEL = "gnani/gnani-evon-v3.3-30B-A3B"
PORT = 8000

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm>=0.12.0", "huggingface_hub[hf_transfer]")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)
hf_cache = modal.Volume.from_name("evon-hf-cache", create_if_missing=True)
app = modal.App("bolda-khata-evon")


@app.function(
    image=image,
    gpu="H100",
    volumes={"/root/.cache/huggingface": hf_cache},
    secrets=[modal.Secret.from_name("evon-key")],
    timeout=60 * 60,
    scaledown_window=10 * 60,   # shut the GPU down after 10 idle minutes to save credit
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=PORT, startup_timeout=25 * 60)
def serve():
    subprocess.Popen([
        "vllm", "serve", MODEL,
        "--served-model-name", MODEL,
        "--host", "0.0.0.0", "--port", str(PORT),
        "--trust-remote-code",
        "--max-model-len", "16384",      # ledger prompts are short; saves KV-cache memory
        "--api-key", os.environ["EVON_API_KEY"],
    ])

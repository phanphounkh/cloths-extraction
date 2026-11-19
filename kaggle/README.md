# Running the image model on a Kaggle GPU

The backend can generate images on a Kaggle notebook GPU instead of OpenRouter.
The notebook loads the model and serves `POST /generate` through an ngrok
tunnel; the backend calls that URL.

## One-time setup

1. Create an ngrok account and copy its auth token (https://dashboard.ngrok.com).
2. Pick a token for the GPU server, e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
   The same value goes in the backend's `KAGGLE_API_TOKEN`.

## Each Kaggle session

1. Store the ngrok token as a Kaggle secret (never in the notebook code):
   **Add-ons → Secrets → Add a secret**, name `NGROK_AUTHTOKEN`, paste the value,
   and toggle it **on** for this notebook.
2. New notebook → **Settings**:
   - Accelerator: **GPU T4 x2**
   - Internet: **On** (needed to download the model and reach ngrok)
3. Upload `kaggle/gpu_server.py` and `kaggle/run_tunnel.py` (or clone the repo).

Cell 1 — install:

```python
!pip install -q "diffusers>=0.30" transformers accelerate scipy pyngrok fastapi uvicorn python-multipart pillow
```

Cell 2 — configure and start (keep this cell running):

```python
import os
os.environ["GPU_SERVER_TOKEN"] = "paste-the-server-token"
# NGROK_AUTHTOKEN is read from Kaggle Secrets by run_tunnel.py.
# Optional: os.environ["INPAINT_STEPS"] = "25"

%run run_tunnel.py
```

`GPU_SERVER_TOKEN` is the same kind of secret: you can also store it under
Add-ons → Secrets and read it with `UserSecretsClient().get_secret(...)`.

The cell prints `Public URL (set KAGGLE_BASE_URL to this): https://....ngrok-free.app`.
The first run downloads the models (about 2.5 GB for the inpainting model plus about 0.5 GB for SegFormer).

Quick check from anywhere:

```sh
curl https://<public-url>/health
```

## Point the backend at it

In the root `.env` (Docker) or `backend/.env` (local):

```env
IMAGE_BACKEND=kaggle
KAGGLE_BASE_URL=https://<public-url>
KAGGLE_API_TOKEN=paste-the-server-token
```

Then restart the backend. `GET /api/v1/health` should show
`"image_backend": "kaggle"` and `"ai_configured": true`.

## Limits to know about

- The URL and the model stop when the Kaggle session ends (sessions have a
  time limit, and idle sessions are shut down). Update `KAGGLE_BASE_URL` after each restart.
- One image is generated at a time; requests queue behind each other.
- Timing on the T4 is not yet measured. The request timeout is `KAGGLE_TIMEOUT_SECONDS`
  (default 300); raise it if generations time out.
- Output is a 512 px square product image. The garment pixels are the original ones; only hidden
  areas are generated. If the design check fails, the response header `X-Needs-Review: 1` is set
  and the image contains only the original pixels (no generated parts).
- Out-of-memory errors come back as HTTP 503 with a message; try a smaller image.

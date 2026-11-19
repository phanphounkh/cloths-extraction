"""Start gpu_server.py on port 8000 and expose it through an ngrok tunnel.

Run this from a Kaggle notebook cell (after installing the requirements and
setting the environment variables). It prints the public URL to paste into
the backend's KAGGLE_BASE_URL.
"""

import os
import threading
import time

import uvicorn
from pyngrok import ngrok

PORT = 8000

ngrok_token = os.environ.get("NGROK_AUTHTOKEN", "")
if not ngrok_token:
    # Kaggle notebooks: Add-ons → Secrets → add NGROK_AUTHTOKEN and attach it.
    from kaggle_secrets import UserSecretsClient

    ngrok_token = UserSecretsClient().get_secret("NGROK_AUTHTOKEN")
if not ngrok_token:
    raise RuntimeError("NGROK_AUTHTOKEN is missing (free account at https://dashboard.ngrok.com).")
# Set the token in memory only. ngrok.set_auth_token() writes a config file and
# fails with "Authtoken already set" when the notebook session runs this again.
from pyngrok import conf  # noqa: E402

conf.get_default().auth_token = ngrok_token

# gpu_server.py loads the model at import time, so import it before serving.
import gpu_server  # noqa: E402

config = uvicorn.Config(gpu_server.app, host="0.0.0.0", port=PORT, log_level="info")
server = uvicorn.Server(config)
threading.Thread(target=server.run, daemon=True).start()

while not server.started:
    time.sleep(0.5)

tunnel = ngrok.connect(PORT, "http")
print("\nPublic URL (set KAGGLE_BASE_URL to this):", tunnel.public_url, flush=True)
print("Keep this cell running; the URL stops working when the session ends.", flush=True)

while True:
    time.sleep(3600)

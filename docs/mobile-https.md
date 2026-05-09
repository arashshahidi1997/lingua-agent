# Mobile testing over LAN — HTTPS workflow

For local CLI / desktop dev, plain HTTP on localhost is fine. **For "Install to Home Screen" on Android Chrome / iOS Safari, browsers require HTTPS** — service workers won't register over plain `http://192.168.x.x`.

Three workflows in increasing fanciness; pick what fits.

## 1. ngrok / Cloudflare Tunnel — instant public HTTPS (recommended for "try it on my phone tonight")

Zero config, zero certs to manage. Tunnels a public HTTPS URL to your local server.

```bash
# Build the React app once so FastAPI can serve it.
npm --prefix web run build

# Terminal 1
.venv/bin/lingua-agent serve --port 8000

# Terminal 2 — pick one
ngrok http 8000
# OR
cloudflared tunnel --url http://localhost:8000
```

You'll get a URL like `https://random-name.ngrok-free.app`. Open it on your phone, install via the browser menu. Caveats: free ngrok URLs change between sessions, and your local server is briefly internet-reachable (basic-auth via `--basic-auth` if that worries you).

## 2. mkcert — local trusted certs (recommended for "I want a stable LAN URL")

`mkcert` installs a local CA into your system trust store and generates a per-device cert you can use directly. Phones need the CA installed once.

```bash
# Install mkcert (one time per machine)
sudo apt install mkcert libnss3-tools   # or: brew install mkcert nss

# Trust the local CA on this machine
mkcert -install

# Generate a cert for your LAN hostname / IP. Replace with yours.
mkdir -p ./certs && cd ./certs
mkcert "$(hostname).local" 192.168.178.61 localhost 127.0.0.1
# → produces hostname.local+3.pem  and  hostname.local+3-key.pem

# Run uvicorn directly with the cert
.venv/bin/uvicorn lingua_agent.api.main:app \
  --host 0.0.0.0 --port 8000 \
  --ssl-certfile ./certs/$(hostname).local+3.pem \
  --ssl-keyfile  ./certs/$(hostname).local+3-key.pem
```

On your phone, install the mkcert root CA once (export `mkcert -CAROOT/rootCA.pem`, copy to phone, install via Settings → Security → Install certificate). After that, `https://<hostname>.local:8000` (or the LAN IP) works without warnings, and PWA install prompts appear.

This is the "local-first, no third party" option.

## 3. Tailscale — every device gets a stable HTTPS hostname

If you already use Tailscale or Headscale, every node on your tailnet gets a `*.ts.net` hostname with **automatic HTTPS** via the `tailscale serve` / `tailscale funnel` commands. No certs to manage, works across networks (so your phone reaches your laptop even when you're on different Wi-Fi).

```bash
# On the laptop:
.venv/bin/lingua-agent serve --port 8000
tailscale serve --bg http://localhost:8000

# Tailscale prints the HTTPS URL, something like:
# https://laptop.tail-scale.ts.net
```

Open that URL on the phone (which must also be signed in to your tailnet). Install prompt works.

This is the **best long-term workflow** if you're a Tailscale user already — stable, no per-device cert management, works off-LAN.

## Quick recommendation

| Goal | Pick |
|---|---|
| Just install on my phone tonight | **ngrok** or **cloudflared tunnel** |
| Stable local LAN setup, no third party | **mkcert** + uvicorn `--ssl-*` |
| Already on Tailscale | **`tailscale serve`** |
| In production | A real reverse proxy (Caddy, Traefik, nginx) with Let's Encrypt — out of scope for dev. |

## What still works without HTTPS

The app itself runs fine over plain HTTP — you can use it via `http://192.168.x.x:8000` from your phone's browser today. You just won't see the install prompt and the service worker won't register. So:

- **Reading / browsing / ingest / review / tutor**: works over plain HTTP.
- **Install to Home Screen**: needs HTTPS.
- **Offline cache**: needs HTTPS (because no service worker).
- **Push notifications** (future): needs HTTPS.

For everyday use of the playground from your phone, plain HTTP is acceptable. Add HTTPS when you want the proper PWA experience.

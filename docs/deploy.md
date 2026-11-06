# Deploying RootLens to Vultr (Phase 5)

Mirrors the pattern already proven for Backtrace (`~/hacktheHill/docs/deploy-vultr.md`):
a single Vultr Ubuntu box running the existing `docker-compose.yml` as-is. Reached by
plain `http://<IP>:8000` / `:3000` for now — no HTTPS or custom domain yet (deliberate
choice: get the deploy working first, add Caddy + `rootlens.brucevo.site` as a
follow-up once this is confirmed).

One difference from Backtrace: RootLens needs a local LLM (`qwen3:8b` via Ollama), not
a hosted API key, so Ollama has to be installed and running on the box itself.

## 1. Provision the instance

Vultr dashboard → Deploy New Server → Cloud Compute → Ubuntu 22.04 LTS.

**Size matters more here than it did for Backtrace.** `qwen3:8b` is a 5.2GB model
running on CPU only (no GPU on a standard Cloud Compute instance) — the Phase 3
benchmark measured 44-51s mean latency per investigation on reasonable local
hardware; expect slower on a small cloud box, and under-provisioning RAM can make it
unusable rather than just slow. Recommended minimum: **4 vCPU / 8GB RAM** (Vultr's
"Regular Performance" tier). Note the public IP once it's up.

## 2. Install Docker and Ollama on the box

```sh
ssh root@<IP>

curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin git

curl -fsSL https://ollama.com/install.sh | sh
```

Ollama binds to `127.0.0.1` by default, which the Docker containers can't reach (they
connect via `host.docker.internal`, which resolves to the host's *external* gateway
IP, not loopback). Make it listen on all interfaces:

```sh
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
EOF
systemctl daemon-reload
systemctl restart ollama

ollama pull qwen3:8b
```

Verify it's reachable from outside loopback before moving on:

```sh
curl http://localhost:11434/api/tags
```

## 3. Get the code and config onto the box

```sh
git clone https://github.com/Bruce1508/RootLens.git
cd RootLens
cp .env.example .env
```

Edit `.env`:
- `POSTGRES_PASSWORD` / `ROOTLENS_READONLY_PASSWORD` — change from the `changeme_*`
  defaults to real random values.
- `API_KEY` — a demo-only token, e.g. `openssl rand -hex 24`. This is what
  `scripts/demo.sh` and the frontend need to send as `Authorization: Bearer <token>`
  on every `POST /api/investigations` (Phase 4 — fails closed if left blank).
- `CORS_ORIGINS` — the URL the frontend will actually be loaded from (the box's own
  `http://<IP>:3000` if serving the frontend from here too, or the Vercel URL if the
  Next.js frontend stays on Vercel and only the API moves to this box).
- `NEXT_PUBLIC_API_BASE_URL` — `http://<IP>:8000`.
- `OLLAMA_MODEL` — leave as `qwen3:8b` (already the default).
- Leave `RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` at their defaults —
  this is exactly the guard Phase 4 built for a box that only runs one model at a time.

## 4. Bring it up

```sh
docker compose up -d --build
```

Unlike Backtrace, RootLens's `Dockerfile` does `COPY . .` (the whole repo, including
`alembic/`), so migrations run fine *inside* the container — no host-side venv
workaround needed:

```sh
docker compose exec api uv run alembic upgrade head
```

Fixture data lives at the repo root (`./data`), mounted into the `api` container at
`/app/data` by `docker-compose.yml`:

```sh
docker compose exec api uv run python -m app.ingestion.cli import --source /app/data/fixtures --reset
```

## 5. Open firewall ports

`ufw` is active by default on a fresh Vultr Ubuntu image, allowing only `22`. Postgres
stays closed — Phase 4 already bound it to `127.0.0.1` only, which is correct and
needs no firewall rule:

```sh
ufw allow 3000/tcp
ufw allow 8000/tcp
ufw reload
```

## 6. Verify

```sh
curl -o /dev/null -w "%{http_code}\n" http://<IP>:8000/api/health
curl -o /dev/null -w "%{http_code}\n" http://<IP>:3000
```

Then run the real demo script against the deployed box (from your own machine or the
box itself) — this is the actual acceptance check, not a localhost run:

```sh
API_BASE_URL=http://<IP>:8000 WEB_BASE_URL=http://<IP>:3000 API_KEY=<the key from .env> ./scripts/demo.sh
```

Watch the printed investigation URL resolve in a browser against the live deploy.

## Status

Steps 1-6 above have **not yet been run against a real Vultr instance** — this is a
runbook drafted from RootLens's actual `docker-compose.yml`/`Dockerfile`/`Makefile`
and the proven Backtrace precedent, not yet verified against a live deploy. Update
this section once it has been.

## Not done yet (deliberately out of scope for this pass)

- **HTTPS / custom domain** (`rootlens.brucevo.site` via Caddy): the plan's original
  ask, deferred until the plain-IP deploy above is confirmed working. Needs a DNS
  record for `brucevo.site` pointing at the box's IP, plus a small Caddy config
  (`reverse_proxy` to `localhost:3000`/`:8000`, Caddy issues the cert automatically on
  first request) — a follow-up, not a redo of the steps above.

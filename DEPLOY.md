# Deploy to Hostinger VPS

Single-host deployment. All services run on one VPS behind Caddy (auto SSL).

```
   user → 443 → Caddy → Next.js (3000) + FastAPI (8000) → Postgres + Redis + Worker
```

Time to first deploy: ~30 minutes.

---

## Prerequisites

- A **Hostinger VPS or Cloud Hosting** plan (KVM is fine; ~2 GB RAM, 2 vCPU minimum)
- A **domain** with an A record pointed at the VPS IP (e.g. `demo.yourdomain.com → 203.0.113.42`)
- SSH access to the VPS as a sudoer user
- The GitHub repo for this project (push the local repo first if you haven't)

---

## 1. One-time VPS setup

SSH in and install Docker + git:

```bash
ssh you@your-vps-ip

# Docker + compose plugin
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # or log out and back in

# Git
sudo apt-get update && sudo apt-get install -y git

# Firewall (Hostinger panel usually does this — but verify)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

## 2. Clone the repo

```bash
cd /opt
sudo mkdir ingest-insight-act && sudo chown $USER:$USER ingest-insight-act
git clone https://github.com/YOUR_USER/ingest-insight-act.git ingest-insight-act
cd ingest-insight-act
```

## 3. Configure `.env.production`

```bash
cp .env.production.example .env.production
nano .env.production
```

Fill in **at minimum**:

| Variable | Value |
|---|---|
| `DOMAIN` | `demo.yourdomain.com` (must match your DNS A record) |
| `POSTGRES_PASSWORD` | a long random string (`openssl rand -hex 32`) |
| `SECRET_KEY` | another long random string |
| `MOCK_CLAUDE` | `true` (keep mock for the demo — flip to `false` once you set a real key) |
| `ANTHROPIC_API_KEY` | only needed if `MOCK_CLAUDE=false` |
| `DEV_TENANT_ID` | a UUID you choose — this is the **single** tenant the harness can drive (`uuidgen`) |

> The dev-bypass header is locked to this exact UUID, so visitors can't seed or query any other tenant.

## 4. First boot

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Watch logs as Caddy provisions the Let's Encrypt cert (takes ~30 s):

```bash
docker compose -f docker-compose.prod.yml logs -f caddy
```

When you see `certificate obtained successfully`, hit `https://demo.yourdomain.com/health` — should return `{"status":"ok"}`.

## 5. Seed the demo tenant

The tenant row needs to exist before the harness can use it:

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U app_user -d ingest_insight_act <<EOF
INSERT INTO tenants (id, name, slug)
VALUES ('YOUR-DEV-TENANT-ID', 'Demo Tenant', 'demo')
ON CONFLICT (id) DO NOTHING;
EOF
```

(Replace `YOUR-DEV-TENANT-ID` with the exact UUID you put in `DEV_TENANT_ID`.)

## 6. Try it

Open `https://demo.yourdomain.com/harness`, paste your `DEV_TENANT_ID` into Step 1, click **Seed Mock Data**, walk Steps 5–8. Mock Claude returns canned JSON instantly so the full pipeline works without an API key.

---

## Updating

Push to `main`, then on the VPS:

```bash
cd /opt/ingest-insight-act
./scripts/deploy.sh
```

The script pulls, rebuilds changed images, applies any new SQL migrations, restarts the stack.

---

## Production hardening checklist

The current setup is **demo-grade**, not enterprise. Before opening it to real customer data:

- [ ] Remove or rotate the dev bypass — set `DEV_TENANT_ID=` (empty) so all auth goes through real Supabase JWT
- [ ] Add `--workers 4` to uvicorn once the VPS has enough cores
- [ ] Enable Postgres backups (`pg_dump | restic` cron, or Hostinger's snapshot feature)
- [ ] Add `fail2ban` for SSH brute-force protection
- [ ] Tighten Caddy with explicit `header_up Host` rewriting if you front it with a CDN
- [ ] Set up uptime monitoring (UptimeRobot is free) on `/health`
- [ ] Cap your `ANTHROPIC_API_KEY` with a monthly spend limit at console.anthropic.com

---

## Troubleshooting

**Caddy keeps retrying SSL**: DNS A record isn't pointed at the VPS yet, or port 80 is blocked. Caddy needs 80 for the ACME HTTP-01 challenge.

**`/api/v1/...` returns 502**: API container crashed. Check `docker compose logs api`. Most common: bad `DATABASE_URL` or missing migration.

**Seed returns 403 "Dev tenant ID mismatch"**: the UUID in your `X-Dev-Tenant-Id` header doesn't match `DEV_TENANT_ID` in `.env.production`.

**Out of memory**: rebuild with `--memory 1g` limits on each service, or upgrade the VPS plan. Postgres alone needs ~256 MB; Next.js prod is ~150 MB; FastAPI ~120 MB; worker ~120 MB; Redis ~30 MB.

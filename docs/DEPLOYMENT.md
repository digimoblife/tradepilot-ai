# TradePilot AI — VPS Deployment Guide

## Topology

```text
Internet
  │
  ▼
Host Nginx (ports 80 / 443)  ← TLS managed by Certbot
  │
  │  proxy_pass http://127.0.0.1:8181
  │
  ▼
TradePilot Gateway (Docker, port 8181, HTTP only)
  │
  ├── Frontend (Next.js, internal port 3000)
  └── Backend API (FastAPI, internal port 8000)
       └── PostgreSQL (internal port 5432)
  └── Worker (no host port)
```

All TradePilot containers run inside a single Docker Compose project named `tradepilot-ai`.
The gateway binds to `127.0.0.1:8181` — only the host Nginx can reach it.

Other VPS projects (ports 3000, 3001, 3005, 5432-5435, 8080, 19999, etc.) are never touched.

---

## Prerequisites

- Docker and Docker Compose plugin installed on the VPS
- Git
- `bash`, `curl`, `pip` (for Alembic migrations)
- Host Nginx configured with Certbot (TLS)

---

## Initial VPS Bootstrap

### 1. Create directories

```bash
sudo mkdir -p /opt/tradepilot-ai/{repository,env,deployment-state}
```

### 2. Clone the repository

```bash
sudo git clone https://github.com/digimoblife/tradepilot-ai.git /opt/tradepilot-ai/repository
```

### 3. Create the production environment file

```bash
sudo touch /opt/tradepilot-ai/env/production.env
sudo chmod 600 /opt/tradepilot-ai/env/production.env
```

Edit `/opt/tradepilot-ai/env/production.env` and add:

```env
APP_ENV=production
POSTGRES_PASSWORD=<strong-random-password>
GEMINI_API_KEY=<your-gemini-key>
DEEPSEEK_API_KEY=<your-deepseek-key>
TRADEPILOT_GATEWAY_PORT=8181
LOG_LEVEL=INFO
```

### 4. Set ownership

```bash
sudo chown -R <deploy-user>:<deploy-group> /opt/tradepilot-ai
```

### 5. Configure host Nginx

Create a server block in `/etc/nginx/sites-available/tradepilot`:

```nginx
server {
    listen 80;
    server_name tradepilot.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name tradepilot.example.com;

    ssl_certificate     /etc/letsencrypt/live/tradepilot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tradepilot.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8181;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/tradepilot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 6. Obtain TLS certificate

```bash
sudo certbot --nginx -d tradepilot.example.com
```

### 7. Verify gateway port

```bash
sudo ss -tlnp | grep 8181
```

Port 8181 should be free before the first deployment.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TRADEPILOT_DEPLOY_DIR` | `/opt/tradepilot-ai/repository` | Git repository working tree |
| `TRADEPILOT_COMPOSE_PROJECT` | `tradepilot-ai` | Docker Compose project name (scoped) |
| `TRADEPILOT_COMPOSE_FILE` | `docker-compose.production.yml` | Compose file relative to deploy dir |
| `TRADEPILOT_ENV_FILE` | `/opt/tradepilot-ai/env/production.env` | Production environment variables |
| `TRADEPILOT_STATE_DIR` | `/opt/tradepilot-ai/deployment-state` | Deployment state (revisions) |
| `TRADEPILOT_GATEWAY_PORT` | `8181` | Gateway host port (127.0.0.1 only) |
| `TRADEPILOT_REVISION` | (origin/main) | Git ref to deploy |
| `TRADEPILOT_RETRY_SECONDS` | 5 | Seconds between health-check retries |
| `TRADEPILOT_RETRY_ATTEMPTS` | 12 | Max health-check retries |
| `POSTGRES_PASSWORD` | *(required)* | PostgreSQL password |
| `GEMINI_API_KEY` | *(optional)* | Google Gemini API key |
| `DEEPSEEK_API_KEY` | *(optional)* | DeepSeek API key |
| `LOG_LEVEL` | `INFO` | Log level |

---

## Operations

### First deployment

```bash
cd /opt/tradepilot-ai/repository
sudo ./infra/deploy/deploy.sh
```

### Normal update (latest production branch)

```bash
cd /opt/tradepilot-ai/repository
sudo ./infra/deploy/deploy.sh
```

### Deploy a specific Git revision

```bash
sudo TRADEPILOT_REVISION=v1.2.3 ./infra/deploy/deploy.sh
```

### Verify health

```bash
curl -sf http://127.0.0.1:8181/health
curl -sf http://127.0.0.1:8181/health/ready
```

### View scoped logs

```bash
docker compose -p tradepilot-ai logs -f
docker compose -p tradepilot-ai logs -f backend
docker compose -p tradepilot-ai logs -f worker
```

### Rollback

```bash
cd /opt/tradepilot-ai/repository
sudo ./infra/deploy/rollback.sh
```

The rollback script restores the previously recorded Git revision, rebuilds images,
runs migrations, and restarts services.  Named volumes (PostgreSQL and evidence)
are never removed during rollback.

### Failure recovery

If a deployment fails:

1. Check logs: `docker compose -p tradepilot-ai logs --tail=50`
2. Fix the issue and re-deploy, or
3. Run `./infra/deploy/rollback.sh` to restore the previous revision.

### Verify volumes

```bash
docker volume ls | grep tradepilot-ai
```

Expected: `tradepilot-ai_pgdata` and `tradepilot-ai_evidence_data`.

### Confirm other projects are untouched

```bash
docker compose -p <other-project> ps
```

All other Compose projects should remain in their previous state.

---

## Deployment Script Details

The deployment script (`infra/deploy/deploy.sh`):

1. **Validates** the environment (directory, Git, env file, Docker, port safety).
2. **Records** the current Git revision to `$STATE_DIR/previous_revision`.
3. **Fetches** and **checks out** the requested revision.
4. **Builds** production Docker images.
5. **Runs database migrations** via Alembic (`alembic upgrade head`).
6. **Starts services** with `docker compose ... up -d`.
7. **Verifies** container states (postgres, backend, worker, frontend, gateway).
8. **Waits for health checks** (`/health` and `/health/ready` via gateway).
9. **Fails** with non-zero exit if any step fails.

## Rollback Script Details

The rollback script (`infra/deploy/rollback.sh`):

1. **Reads** the previous revision from `$STATE_DIR/previous_revision`.
2. **Refuses** if no valid previous revision exists.
3. **Checks out** the previous revision.
4. **Builds** images, **runs** migrations.
5. **Restarts** services.
6. **Waits for health checks**.
7. **Never removes** PostgreSQL or evidence named volumes.

## Host Nginx Boundary

The deployment scripts **never**:

- Edit `/etc/nginx` automatically
- Restart or reload host Nginx
- Run Certbot
- Bind to host ports 80 or 443
- Use the TP-1702 self-signed certificate in production

Host Nginx configuration and TLS certificate management remain manual operational tasks.

# VPS Dashboard Deployment

This is the production path for the Supabase-first FastAPI dashboard. The VPS
runs two private localhost services:

- `nattome-dashboard.service`: the authenticated FastAPI/Jinja web app.
- `nattome-dashboard-worker.service`: the separate queue worker that claims
  manual runs, executes pipeline work, uploads artifacts to Supabase Storage,
  and updates Supabase Postgres status rows.

Supabase is the production system of record. The VPS should not be treated as
the dashboard database or artifact store.

These commands assume Ubuntu 24.04, root shell access, and this repository:

```text
https://github.com/alsontanwork4-cmyk/Nattome-TikTok-Pipeline.git
```

## 1. Inspect The VPS

Before replacing an existing deployment, check active services, ports, and disk
usage.

```bash
pwd
ls -lah /root /home /opt /var/www 2>/dev/null
du -h --max-depth=1 /root /home /opt /var/www 2>/dev/null | sort -h
systemctl --type=service --state=running
ss -tulpn
```

If there are old folders you are not sure about, move them into a dated
quarantine folder instead of deleting them immediately.

```bash
mkdir -p /root/vps-cleanup-quarantine/$(date +%F)
mv /path/to/old-folder /root/vps-cleanup-quarantine/$(date +%F)/
```

## 2. Install System Packages

```bash
apt update
apt install -y git python3 python3-venv nginx ufw
```

## 3. Deploy The Repository

Use `/opt/nattome-pipeline` as the application directory.

```bash
mkdir -p /opt
cd /opt
git clone https://github.com/alsontanwork4-cmyk/Nattome-TikTok-Pipeline.git nattome-pipeline
cd /opt/nattome-pipeline
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If the VPS should run a specific branch:

```bash
git fetch origin
git checkout YOUR_BRANCH
```

## 4. Configure Supabase

Create the Supabase project before starting the services:

- For a fresh project, run `docs/supabase-dashboard-schema.sql` in Supabase SQL
  Editor, then review the dashboard data contract in
  `docs/supabase-dashboard-data-contract.md`.
- For an existing project, apply the idempotent migration files in order:
  `docs/migrations/20260510_agent_settings_versions.sql`, then
  `docs/migrations/20260510_agent_trace_events.sql`. Run both idempotent agent migrations before restarting existing services so the web app, worker, and
  PostgREST schema cache agree on `agent_settings_versions`,
  `save_agent_settings_version`, and `agent_trace_events`.
- Enable Supabase Auth and create the owner user who may sign in to the dashboard.
- Create the Storage bucket named by `SUPABASE_STORAGE_BUCKET`; the examples use
  `dashboard-artifacts`.
- Keep the service-role key server-side only. It belongs in the VPS
  `EnvironmentFile`, never in browser-visible templates or client code.

## 5. Add Runtime Environment

Write the service environment file with production mode, Supabase access,
workspace paths, Storage bucket names, and pipeline credentials.

```bash
cat >/opt/nattome-pipeline/.env <<'EOF'
DASHBOARD_RUNTIME_MODE=production
DASHBOARD_WORKSPACE_PATH=/opt/nattome-pipeline
DASHBOARD_RUNS_PATH=/opt/nattome-pipeline/runs
DASHBOARD_DATA_PATH=/opt/nattome-pipeline/data
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_ANON_KEY=replace_me
SUPABASE_SERVICE_ROLE_KEY=replace_me
SUPABASE_STORAGE_BUCKET=dashboard-artifacts
APIFY_TOKEN=replace_me
GEMINI_API_KEY=replace_me
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
EOF
chmod 600 /opt/nattome-pipeline/.env
```

Environment ownership:

| Variable | Used by | Purpose |
|---|---|---|
| `DASHBOARD_RUNTIME_MODE=production` | Web, worker | Enables production dashboard behavior. |
| `DASHBOARD_WORKSPACE_PATH=/opt/nattome-pipeline` | Web, worker, import scripts | Root for repo-relative paths and migration artifacts. |
| `DASHBOARD_RUNS_PATH` | Web, worker, import scripts | Local run folder location for migration and temporary pipeline output. |
| `DASHBOARD_DATA_PATH` | Web, worker, import scripts | Local data folder location for configs and migration inputs. |
| `SUPABASE_URL=https://YOUR-PROJECT.supabase.co` | Web, worker, import scripts | Supabase project API URL. |
| `SUPABASE_ANON_KEY=replace_me` | Web | Supabase Auth browser/session boundary. |
| `SUPABASE_SERVICE_ROLE_KEY=replace_me` | Server-side web code, worker, import scripts | Supabase Postgres and Storage service operations. |
| `SUPABASE_STORAGE_BUCKET=dashboard-artifacts` | Web, worker, import scripts | Bucket for reports, source videos, JSON snapshots, workbooks, and other artifacts. |
| `APIFY_TOKEN` | Worker | TikTok scrape execution. |
| `GEMINI_API_KEY` | Worker | Nattome POV report generation. GEMINI_API_KEY remains in the VPS EnvironmentFile and is never stored in dashboard-managed agent settings. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Worker | Optional report delivery. |

## 6. Add The FastAPI Service

The production ASGI command is:

```bash
/opt/nattome-pipeline/.venv/bin/uvicorn dashboard.app:create_app --factory --host 127.0.0.1 --port 8765
```

Install the web service:

```bash
cat >/etc/systemd/system/nattome-dashboard.service <<'EOF'
[Unit]
Description=Nattome Supabase FastAPI dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/nattome-pipeline
EnvironmentFile=/opt/nattome-pipeline/.env
ExecStart=/opt/nattome-pipeline/.venv/bin/uvicorn dashboard.app:create_app --factory --host 127.0.0.1 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now nattome-dashboard
systemctl status nattome-dashboard --no-pager
curl -fsS http://127.0.0.1:8765/healthz
```

Expected health output:

```json
{"status":"ok"}
```

## 7. Add The Worker Service

Run the queue worker as a separate service so long-running analysis never blocks
FastAPI request handling. The worker should use the same environment file as the
web app because it needs Supabase Postgres, Supabase Storage, workspace paths,
and pipeline credentials.

```bash
cat >/etc/systemd/system/nattome-dashboard-worker.service <<'EOF'
[Unit]
Description=Nattome dashboard Supabase worker
After=network-online.target nattome-dashboard.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/nattome-pipeline
EnvironmentFile=/opt/nattome-pipeline/.env
ExecStart=/opt/nattome-pipeline/.venv/bin/python -m dashboard.worker --worker-id vps-worker-1 --poll-interval 15
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now nattome-dashboard-worker
systemctl status nattome-dashboard-worker --no-pager
```

The worker contract is:

- Claim one queued `manual_runs` row at a time.
- Mark the matching `runs` row as `running`, then `succeeded`, `failed`, or
  `canceled`.
- Upload large outputs to Supabase Storage under stable `runs/<run_id>/...`
  object paths.
- Upsert `run_outputs` metadata for every uploaded object.
- Resolve active Gemini agent settings from Supabase, local config, or defaults.
- Live tracing writes compact `agent_trace_events` rows while Gemini work is
  running. These rows contain status, timing, candidate references, compact
  uploaded-file/usage metadata, artifact references, and sanitized error
  summaries; full Gemini responses stay in Supabase Storage artifacts.
- Store concise failure summaries only; do not write secrets or full
  environment dumps to Supabase.

## 8. Put Nginx In Front

Nginx terminates public HTTP/HTTPS and proxies to the private FastAPI listener.
Authentication remains Supabase Auth inside the dashboard, so do not add a
second basic-auth gate unless you explicitly need an emergency extra layer.

Replace `your-domain.com` with the real domain. Use `_` temporarily only when
testing by IP address.

```bash
cat >/etc/nginx/sites-available/nattome-dashboard <<'EOF'
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/nattome-dashboard /etc/nginx/sites-enabled/nattome-dashboard
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

Open the firewall:

```bash
ufw allow OpenSSH
ufw allow 'Nginx HTTP'
ufw allow 'Nginx HTTPS'
ufw --force enable
```

If you point a domain to the VPS, add HTTPS with Certbot:

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

## 9. Backups

Supabase Postgres backups protect metadata: runs, statuses, settings versions,
manual-run records, raw/selected video metadata, and artifact rows.
Enable Supabase Postgres backups in the Supabase project and periodically test a
restore into a separate project before relying on the backup plan.

Supabase Storage export protects large artifacts: source videos, reports,
workbooks, raw scrape JSON, evidence snapshots, Gemini responses, and any other
objects in `SUPABASE_STORAGE_BUCKET`. Schedule a Storage export or object sync
to a separate backup target. The export must preserve bucket name, object path,
size, and checksum when available so `run_outputs` rows can be reconciled after
a restore.

Keep the VPS `.env` outside the repository and include it in the server backup
plan through your secrets manager or encrypted host backup. Do not commit it.

## 11. Common Operations

Check logs:

```bash
journalctl -u nattome-dashboard -n 100 --no-pager
journalctl -u nattome-dashboard-worker -n 100 --no-pager
```

Deploy new code:

```bash
cd /opt/nattome-pipeline
git pull
. .venv/bin/activate
pip install -r requirements.txt
# Existing deployments only, when these files have not been applied yet:
# run docs/migrations/20260510_agent_settings_versions.sql in Supabase SQL Editor
# run docs/migrations/20260510_agent_trace_events.sql in Supabase SQL Editor
systemctl restart nattome-dashboard
systemctl restart nattome-dashboard-worker
```

Stop services:

```bash
systemctl stop nattome-dashboard-worker
systemctl stop nattome-dashboard
```

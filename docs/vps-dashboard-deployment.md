# VPS Dashboard Deployment

This dashboard is a Python HTTP app. On a VPS, run it as a private localhost
service and expose it through Nginx with basic authentication.

These commands assume Ubuntu 24.04, root shell access, and this repository:

```text
https://github.com/alsontanwork4-cmyk/Nattome-TikTok-Pipeline.git
```

## 1. Inspect Before Cleaning

Do this first so you do not delete active services or data by accident.

```bash
pwd
ls -lah /root /home /opt /var/www 2>/dev/null
du -h --max-depth=1 /root /home /opt /var/www 2>/dev/null | sort -h
systemctl --type=service --state=running
ss -tulpn
```

If there are old folders you are not sure about, quarantine them instead of
deleting them:

```bash
mkdir -p /root/vps-cleanup-quarantine/$(date +%F)
mv /path/to/old-folder /root/vps-cleanup-quarantine/$(date +%F)/
```

After the dashboard has been running for a few days and nothing is missing, you
can remove quarantined folders:

```bash
rm -rf /root/vps-cleanup-quarantine/YYYY-MM-DD/old-folder
```

## 2. Install System Packages

```bash
apt update
apt install -y git python3 python3-venv nginx apache2-utils ufw
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

If you need the VPS to use a branch other than the default branch:

```bash
git fetch origin
git checkout codex/run-nattome-discovery-test1
```

## 4. Add Runtime Secrets

Only add the keys you need. The dashboard can render existing artifacts without
tokens, but manual pipeline runs need the Apify and Gemini keys.

```bash
cat >/opt/nattome-pipeline/.env <<'EOF'
APIFY_TOKEN=replace_me
GEMINI_API_KEY=replace_me
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
EOF
chmod 600 /opt/nattome-pipeline/.env
```

## 5. Start The Dashboard With systemd

```bash
cat >/etc/systemd/system/nattome-dashboard.service <<'EOF'
[Unit]
Description=Nattome dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/nattome-pipeline
EnvironmentFile=/opt/nattome-pipeline/.env
ExecStart=/opt/nattome-pipeline/.venv/bin/python -m dashboard.web --host 127.0.0.1 --port 8765 --workspace /opt/nattome-pipeline
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

```text
ok
```

## 6. Put Nginx In Front

Create a basic-auth user:

```bash
htpasswd -c /etc/nginx/.htpasswd nattome
```

Create the Nginx site. Replace `your-domain.com` with a real domain if you have
one. If you only have an IP address, use `_` as `server_name`.

```bash
cat >/etc/nginx/sites-available/nattome-dashboard <<'EOF'
server {
    listen 80;
    server_name _;

    auth_basic "Nattome Dashboard";
    auth_basic_user_file /etc/nginx/.htpasswd;

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
ufw --force enable
```

Now visit:

```text
http://YOUR_VPS_IP/
```

## 7. Optional HTTPS

If you point a domain to the VPS, add HTTPS with Certbot:

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

## 8. Upload Existing Local Artifacts

The dashboard is most useful when `data/`, `runs/`, and `outputs/` are present
on the VPS. From your Windows machine, upload them with `scp`:

```powershell
scp -r data outputs runs root@YOUR_VPS_IP:/opt/nattome-pipeline/
```

Then rebuild the dashboard index on the VPS:

```bash
cd /opt/nattome-pipeline
. .venv/bin/activate
python -c "from dashboard.indexer import index_pipeline_artifacts; print(index_pipeline_artifacts())"
systemctl restart nattome-dashboard
```

For the Supabase-first dashboard migration, import historical Run Folder
artifacts once after the files are present on the VPS. The importer uploads each
file under a stable `runs/<run_id>/...` Storage object path, then upserts the
matching `runs` and `run_outputs` metadata rows.

```bash
cd /opt/nattome-pipeline
. .venv/bin/activate
export DASHBOARD_WORKSPACE_PATH=/opt/nattome-pipeline
export SUPABASE_URL="https://YOUR-PROJECT.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="replace_me"
export SUPABASE_STORAGE_BUCKET="dashboard-artifacts"
python -m dashboard.legacy_import \
  --workspace /opt/nattome-pipeline \
  --storage-bucket dashboard-artifacts
```

If the old dashboard SQLite file has curation labels or notes that are not
recoverable from artifacts, pass it explicitly as a one-time source:

```bash
python -m dashboard.legacy_import \
  --workspace /opt/nattome-pipeline \
  --storage-bucket dashboard-artifacts \
  --legacy-sqlite /opt/nattome-pipeline/data/dashboard/dashboard.sqlite3
```

Do not configure the new FastAPI dashboard to read SQLite at runtime. This
import is a migration aid only; rerunning it is safe because run and artifact
metadata are upserted by stable keys.

## 9. Common Operations

Check logs:

```bash
journalctl -u nattome-dashboard -n 100 --no-pager
```

Deploy new code:

```bash
cd /opt/nattome-pipeline
git pull
. .venv/bin/activate
pip install -r requirements.txt
systemctl restart nattome-dashboard
```

Stop the dashboard:

```bash
systemctl stop nattome-dashboard
```

# ZeroTax AI — Deployment Guide

Complete guide to deploying ZeroTax AI on every major platform.

---

## Quick Start (Local)

```bash
# 1. Clone the repo
git clone https://github.com/username1176/Claude.git
cd Claude

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key
export ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# 4. Run
streamlit run app.py
```

Open http://localhost:8501 → Register → Settings → Save API key → New Plan

---

## Option A — Streamlit Community Cloud (Free)

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=username1176/Claude&branch=main&mainModule=app.py)

**Steps:**
1. Fork this repository on GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → "New app"
3. Select your fork → Branch: `main` → Main file: `app.py`
4. Click "Advanced settings" → Add secrets:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-api03-..."
   OPENAI_API_KEY = "sk-..."       # optional
   ```
5. Deploy

**Limitations:** Free tier has 1 GB RAM; the PDF generator and charts work fine. SQLite is ephemeral between deploys — users set API keys per session or via secrets.

---

## Option B — Docker (Self-Hosted)

```bash
# Build
docker build -t zerotax-ai .

# Run (with persistent data volume)
docker run -d \
  --name zerotax \
  -p 8501:8501 \
  -v zerotax_data:/data \
  -e ANTHROPIC_API_KEY=sk-ant-api03-... \
  -e OPENAI_API_KEY=sk-... \
  zerotax-ai

# Or with docker compose
cp .env.example .env
# Edit .env with your keys
docker compose up -d
```

Access at http://localhost:8501

**Production tip:** Put nginx in front with SSL:
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate     /etc/ssl/your-cert.pem;
    ssl_certificate_key /etc/ssl/your-key.pem;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## Option C — Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/username1176/Claude&envs=ANTHROPIC_API_KEY,OPENAI_API_KEY&ANTHROPIC_API_KEYDesc=Your+Anthropic+API+key&OPENAI_API_KEYDesc=Your+OpenAI+key+optional)

**Steps:**
1. Click button above or go to [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo → Select this repo
3. Add environment variables:
   - `ANTHROPIC_API_KEY` = your key
   - `OPENAI_API_KEY` = your key (optional)
4. Railway auto-detects `railway.toml` and `Dockerfile`
5. Add a Volume → Mount path: `/data`

**Cost:** ~$5–10/month on hobby plan for typical usage.

---

## Option D — Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/username1176/Claude)

**Steps:**
1. Click button above or go to [render.com](https://render.com)
2. New → Web Service → Connect GitHub repo
3. Runtime: Docker → Dockerfile path: `./Dockerfile`
4. Add environment variables in the Render dashboard
5. Add a Disk: Mount path `/data`, Size: 1 GB
6. Deploy

**Cost:** Starter plan ~$7/month. Disk is $0.25/GB/month.

---

## Option E — AWS EC2 / DigitalOcean / VPS

```bash
# On your server (Ubuntu 22.04+):

# 1. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Clone and configure
git clone https://github.com/username1176/Claude.git
cd Claude
cp .env.example .env
nano .env   # Add your API keys

# 3. Deploy with compose
docker compose up -d

# 4. Configure firewall
sudo ufw allow 8501/tcp
sudo ufw enable

# 5. Set up auto-restart on server reboot
# (docker compose handles this via restart: unless-stopped)
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | Claude claude-sonnet-4-6 API key — get at [console.anthropic.com](https://console.anthropic.com) |
| `OPENAI_API_KEY` | No | For RAG embeddings; app works without it |
| `ZEROTAX_DB` | No | Path for SQLite DB (default: `zerotax.db` in working dir) |

---

## Production Checklist

- [ ] Set `ANTHROPIC_API_KEY` in environment (not in code)
- [ ] Use a persistent volume for `/data` (prevents data loss on redeploy)
- [ ] Put a reverse proxy (nginx/Caddy) in front with SSL
- [ ] Set up regular SQLite backups (`sqlite3 zerotax.db .dump > backup.sql`)
- [ ] Consider rate limiting on the nginx layer to prevent API abuse
- [ ] Review Anthropic's usage policies before sharing publicly

---

## Upgrading

```bash
git pull origin main
docker compose pull
docker compose up -d --build
```

## Support

- Issues: github.com/username1176/Claude/issues
- Anthropic API docs: docs.anthropic.com
- Streamlit docs: docs.streamlit.io

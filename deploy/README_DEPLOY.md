# Crashout Recovery — Vultr production deploy guide

**OS:** Ubuntu 26.04 (or 24.04 LTS)  
**Stack:** nginx · systemd · uvicorn · FastAPI

## Production layout (exact)

| Item | Value |
|------|--------|
| Project root | `/root/crashoutrecovery` |
| App | `main:app` |
| Uvicorn | `127.0.0.1:8777` |
| Static | `/root/crashoutrecovery/static` |
| Templates | `/root/crashoutrecovery/templates` |
| Venv | `/root/crashoutrecovery/venv` |
| Domain | `crashoutrecovery.app` |
| Server IP | `144.202.65.200` |

```text
/root/crashoutrecovery/
├── app/
├── static/
├── templates/
├── main.py
├── requirements.txt
├── .env
├── venv/
└── deploy/
```

---

## 1. Install the app on Vultr

```bash
ssh root@144.202.65.200
cd /root/crashoutrecovery

apt-get update -y
apt-get install -y python3 python3-venv python3-pip
python3 -m venv /root/crashoutrecovery/venv
source /root/crashoutrecovery/venv/bin/activate
pip install -U pip
pip install -r requirements.txt

cp .env.example .env
nano .env
```

Required:

```env
CRASHOUT_ENV=production
CRASHOUT_JWT_SECRET=long-random-secret-at-least-32-characters
```

---

## 2. GoDaddy DNS

| Type | Name | Value |
|------|------|--------|
| A | `@` | `144.202.65.200` |
| A | `www` | `144.202.65.200` |

```bash
dig +short crashoutrecovery.app
dig +short www.crashoutrecovery.app
# both should return 144.202.65.200
```

---

## 3. Run `setup.sh`

```bash
chmod +x /root/crashoutrecovery/deploy/*.sh
sudo bash /root/crashoutrecovery/deploy/setup.sh
```

- Installs nginx  
- Opens UFW **80** and **443**  
- Copies `nginx.conf` → `/etc/nginx/sites-available/crashoutrecovery`  
- Symlinks → `/etc/nginx/sites-enabled/crashoutrecovery`  
- Runs `nginx -t` and `systemctl reload nginx`

### Test nginx

```bash
sudo nginx -t
sudo systemctl status nginx
curl -I http://127.0.0.1/
curl -I http://144.202.65.200/
curl -I http://127.0.0.1/static/crashout-recovery.css
```

---

## 4. Enable `crashout.service`

```bash
sudo cp /root/crashoutrecovery/deploy/crashout.service /etc/systemd/system/crashout.service
sudo systemctl daemon-reload
sudo systemctl enable crashout
sudo systemctl start crashout
sudo systemctl status crashout
```

### Test systemd / app

```bash
sudo journalctl -u crashout -f
curl -sS http://127.0.0.1:8777/health
curl -sS http://127.0.0.1/health
curl -sS http://144.202.65.200/health
```

Expect `{"status":"ok",...}`. Keep port **8777** closed on the public firewall.

---

## 5. Run `ssl.sh`

After DNS points at `144.202.65.200`:

```bash
CERTBOT_EMAIL=you@example.com sudo -E bash /root/crashoutrecovery/deploy/ssl.sh
```

Certificates for `crashoutrecovery.app` and `www.crashoutrecovery.app`; HTTPS auto-configured in nginx.

```bash
curl -I https://crashoutrecovery.app/health
curl -I https://www.crashoutrecovery.app/health
```

---

## 6. Updates

```bash
cd /root/crashoutrecovery
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crashout
sudo cp deploy/nginx.conf /etc/nginx/sites-available/crashoutrecovery
sudo nginx -t && sudo systemctl reload nginx
```

---

## Checklist

- [ ] Code at `/root/crashoutrecovery`
- [ ] venv at `/root/crashoutrecovery/venv`
- [ ] Production `.env` (JWT secret set)
- [ ] DNS A `@` and `www` → `144.202.65.200`
- [ ] `setup.sh` OK
- [ ] `crashout.service` active
- [ ] `/health` via nginx
- [ ] `ssl.sh` OK

# Tunnel and token maintenance (avoid repeat setup)

## 1. Keep the Cloudflare Tunnel running

**Option A – Start at login (recommended)**  
Install the launchd job so the tunnel starts when you log in and restarts if it crashes:

```bash
cd "/Users/avi.horowitz/Documents/LayoffTracker -74 - with earning event copy"
cp cloudflared-launchd.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/cloudflared-launchd.plist
```

To stop or uninstall later:
```bash
launchctl unload ~/Library/LaunchAgents/cloudflared-launchd.plist
```

**Option B – Fallback: start if not running**  
Run periodically (e.g. cron every 5 min) or after reboot:
```bash
./start_tunnel_if_needed.sh
```

**Check status:** `./check_cloudflared.sh`

---

## 2. Cloudflared certificate (cert.pem)

- Stored at `~/.cloudflared/cert.pem` after `cloudflared tunnel login`.
- This cert is long-lived; you do **not** need to renew it unless Cloudflare invalidates it or you delete it.
- **Backup once:** `cp ~/.cloudflared/cert.pem ~/Desktop/cloudflared-cert.pem.bak` (or similar). If you ever have to re-run login, you can compare or restore.
- Avoid running `cloudflared tunnel login` again unless the tunnel stops authorizing; it overwrites the cert.

---

## 3. Schwab refresh token

- Stored in **`data/schwab_refresh_token.txt`** (one line, token only).
- **Heartbeat:** The app runs a background heartbeat every 24 hours (when the Flask server is running) so the refresh token is used regularly. That may help avoid expiry; if Schwab still expires it after 7 days, you’ll need to re-run the OAuth flow and paste a new token into `data/schwab_refresh_token.txt`.
- **Backup:** Copy `data/schwab_refresh_token.txt` somewhere safe (e.g. password manager). If you lose it, you must complete the OAuth flow again (tunnel must be up so the redirect to api.avi-marketdata.xyz works).

---

## 4. Quick checklist if something breaks

| Symptom | What to do |
|--------|------------|
| Error 1033 / api.avi-marketdata.xyz not loading | Tunnel down → run `./check_cloudflared.sh`; if not running, start with launchd or `./start_tunnel_if_needed.sh`. |
| Schwab "refresh token expired" | Tunnel must be up, then open the authorize URL, log in, paste redirect URL into `schwab_oauth_get_refresh_token.py`, put new token in `data/schwab_refresh_token.txt`, restart app. |
| cloudflared "certificate" or auth error | Ensure `~/.cloudflared/cert.pem` exists; if you backed it up, restore it. If not, run `./bin/cloudflared tunnel login` again and re-authorize the zone. |

---

## 5. Authorize URL (for Schwab re-auth)

When you need a new refresh token, open this (with tunnel up), then paste the redirect URL into the script:

```
https://api.schwabapi.com/v1/oauth/authorize?client_id=jSGRcUly7Ao8i0gwE8A3bhUOGWQC6tAaXYWc8KJTBKShBgOP&redirect_uri=https%3A%2F%2Fapi.avi-marketdata.xyz%2Fschwab%2Fcallback&response_type=code
```

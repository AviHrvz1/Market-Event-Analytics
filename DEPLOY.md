# Deploy to Git and AWS Elastic Beanstalk

## Prerequisites

- **Git remote:** Ensure `origin` points to your repo, e.g.  
  `git remote add origin https://github.com/AviHrvz1/Market-Event-Analytics.git`
- **AWS CLI:** Install and run `aws configure` (Access Key, Secret Key, region).
- **EB CLI:** `pip install awsebcli`

---

## Environment variables (Beanstalk)

Set these in the Beanstalk environment (Console → your app → Configuration → Software → Environment properties, or `eb setenv KEY=value ...`). The app reads from `os.getenv()`; `app_secrets.py` and `data/` are not on the server.

| Variable | Description |
|----------|-------------|
| `PRIXE_API_KEY` | Prixe.io stock price API |
| `SCHWAB_TOS_API_KEY` | Schwab (TOS) app key |
| `SCHWAB_TOS_API_SECRET` | Schwab app secret |
| `SCHWAB_TOS_REFRESH_TOKEN` | Schwab OAuth refresh token (or use file locally; on Beanstalk use env) |
| `CLAUDE_API_KEY` | Claude AI (optional) |
| `NEWS_API_KEY` | NewsAPI (optional) |

Optional: `SCHWAB_TOS_APP_MACHINE_NAME`, `SCHWAB_HEARTBEAT_INTERVAL_HOURS`, `MAX_ARTICLES_TO_PROCESS`, `PRIXE_PRICE_ENDPOINT`, `PRIXE_BASE_URL`.

---

## One-time setup

1. **Initialize Beanstalk** (once per machine):
   ```bash
   eb init -p python-3.9 layoff-tracker --region us-east-1
   ```
   Use your preferred application name and region (e.g. `us-west-2`).

2. **Create the environment** (once):
   ```bash
   eb create
   ```
   Or create the environment from the AWS Beanstalk console. The included `.ebextensions` config forces a **single instance** (no load balancer).

3. **Set environment variables** in Beanstalk (see table above).

---

## Routine workflow

- **Push to Git only:**  
  `./scripts/push-to-git.sh`  
  Optional message: `./scripts/push-to-git.sh "Your commit message"`

- **Deploy to Beanstalk only:**  
  `./scripts/deploy-to-beanstalk.sh`

- **Push then deploy:**  
  `./scripts/push-and-deploy.sh`  
  Optional message: `./scripts/push-and-deploy.sh "Your commit message"`

---

## Data directory

`data/` is gitignored (uploaded CSVs, `schwab_refresh_token.txt`, etc.). On Beanstalk there is no local `data/` directory. Use the **SCHWAB_TOS_REFRESH_TOKEN** environment variable for the Schwab refresh token. Uploaded account statements in the UI are not persisted across deployments unless you add external storage (e.g. S3).

---

## Private site (no code change)

### Option 1: Cloudflare Access (recommended)

Restrict the site so only you can open it. No application or Beanstalk code changes.

1. **Add your domain to Cloudflare** (DNS only or full proxy). If the app is reached via the raw Beanstalk URL (e.g. `xxx.us-east-1.elasticbeanstalk.com`), add a **custom domain** in Cloudflare that CNAMEs to that hostname so Access can protect it.

2. **Open Cloudflare Zero Trust:**  
   [dash.teams.cloudflare.com](https://dash.teams.cloudflare.com) or Cloudflare dashboard → Zero Trust.

3. **Create an Access application:**  
   Access → Applications → Add an application.

4. **Self-hosted:**  
   Choose **Self-hosted**. Set application name and session duration.

5. **Application domain:**  
   Set to the hostname that points to your app (e.g. `app.yourdomain.com` or the Beanstalk custom domain). Must be a hostname on Cloudflare (your domain).

6. **Policy:**  
   Add a policy: **Include** → **Emails** → add your email (or “Emails ending in” your domain). Save.

7. **Result:**  
   Unauthenticated visitors get a Cloudflare login page. Only your allowed email can reach the app.

### Option 2: IP allowlist (alternative)

1. In **AWS Console** go to **EC2** → **Security Groups**.
2. Find the security group used by your Beanstalk environment (e.g. attached to the environment’s EC2 instance).
3. **Edit inbound rules:** restrict **HTTP (80)** and **HTTPS (443)** to **My IP** or specific CIDR blocks.
4. When your IP changes (e.g. new network), update the rule again.

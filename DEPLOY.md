# Deploy to Git and AWS Elastic Beanstalk

## AWS account (reference)

- **Account ID:** `966441873206`
- **Canonical user ID:** `adf015ae7c0d4722d6115b833bfc53749a8c8aa4dc461d4231691acd647e1269`  
  (Use for IAM or S3 bucket policies if needed.)

To run `eb init` and `eb create`, you still need **access keys**: run `aws configure` and enter your **Access Key ID** and **Secret Access Key** (from IAM → Users → Security credentials → Create access key). The account ID and canonical user ID are not used for login.

## Prerequisites

- **Git remote:** Ensure `origin` points to your repo, e.g.  
  `git remote add origin https://github.com/AviHrvz1/Market-Event-Analytics.git`
- **AWS CLI:** Install and run `aws configure` (Access Key ID, Secret Access Key, region).
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
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for profit alerts |
| `TELEGRAM_CHAT_ID` | Telegram chat ID to receive alerts |

Optional: `SCHWAB_TOS_APP_MACHINE_NAME`, `SCHWAB_HEARTBEAT_INTERVAL_HOURS`, `MAX_ARTICLES_TO_PROCESS`, `PRIXE_PRICE_ENDPOINT`, `PRIXE_BASE_URL`.

**`SCHWAB_TOS_CALLBACK_URL`** — OAuth redirect after Schwab login. Default is `https://api.avi-marketdata.xyz/schwab/callback`. On Beanstalk, set this to the **exact** URL where users land after logging in at Schwab. See **Schwab callback (Option B)** below to use the custom domain and avoid Chrome’s “Dangerous site” warning.

---

## Schwab callback (Option B — custom domain)

To avoid Chrome’s “Dangerous site” warning when returning from Schwab login, use your **custom domain** (e.g. `https://api.avi-marketdata.xyz`) for the callback instead of the raw Elastic Beanstalk URL.

1. **Set the callback URL on Beanstalk** (one-time or after env reset):
   ```bash
   ./scripts/set-schwab-callback-url.sh
   ```
   This sets `SCHWAB_TOS_CALLBACK_URL=https://api.avi-marketdata.xyz/schwab/callback` on the current EB environment. To use a different URL, run:
   ```bash
   SCHWAB_TOS_CALLBACK_URL=https://your-domain.com/schwab/callback ./scripts/set-schwab-callback-url.sh
   ```

2. **Register the same URL in the Schwab developer portal:**
   - Go to [developer.schwab.com](https://developer.schwab.com) (or [beta-developer.schwab.com](https://beta-developer.schwab.com)).
   - Open your app → **Callback URL** / **Redirect URI**.
   - Set it to exactly: `https://api.avi-marketdata.xyz/schwab/callback` (no trailing slash). Save.

3. **Use the app via the custom domain** when doing Schwab setup:
   - Open the app at **https://api.avi-marketdata.xyz** (not the `*.elasticbeanstalk.com` URL).
   - Use “Open Schwab and log in” from there. After Schwab login you’ll be redirected to `api.avi-marketdata.xyz/schwab/callback`, which the app will handle and exchange the code.

Ensure your custom domain (e.g. Cloudflare Tunnel or CNAME) points to the same Beanstalk app so the callback request hits your app.

---

## One-time setup

1. **Initialize Beanstalk** (once per machine):
   ```bash
   eb init -p python-3.9 layoff-tracker --region us-east-1
   ```
   Use your preferred application name and region (e.g. `us-west-2`).

2. **Create the environment** (once). For **Free Tier** (no extra cost), create with **t3.micro** via AWS CLI so the instance type is applied from the start:
   ```bash
   aws elasticbeanstalk create-environment \
--application-name layoff-tracker \
    --environment-name layoff-tracker-prod \
     --solution-stack-name "64bit Amazon Linux 2023 v4.10.0 running Python 3.9" \
     --option-settings file://.elasticbeanstalk/options-t3micro.json \
     --region us-east-1
   ```
   The file `.elasticbeanstalk/options-t3micro.json` sets `SingleInstance`, `IamInstanceProfile=aws-elasticbeanstalk-ec2-role`, and `InstanceTypes=t3.micro` (Free Tier–eligible). The instance profile is required or the environment fails with "Environment must have instance profile associated with it." Alternatively you can use `eb create <env-name>` and then set **Instance types** to **t3.micro** in the console (Configuration → Capacity) once the environment is Ready.

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

## AWS CLI troubleshooting

If the Beanstalk environment stays in **Launching** with no instances, run these in the same region as the environment (e.g. `us-east-1`).

**Default VPC (required for default Beanstalk setup):**
```bash
aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --region us-east-1 --query 'Vpcs[*].{VpcId:VpcId,CidrBlock:CidrBlock}' --output table
```
Expect one VPC. If empty, create a default VPC or use a region that has one.

**Default subnets:**
```bash
aws ec2 describe-subnets --filters "Name=vpc-id,Values=YOUR_VPC_ID" --region us-east-1 --query 'Subnets[*].{SubnetId:SubnetId,AvailabilityZone:AvailabilityZone}' --output table
```

**EC2 On-Demand quota:**
```bash
aws service-quotas get-service-quota --service-code ec2 --quota-code L-1216C47A --region us-east-1 --query 'Quota.{Name:QuotaName,Value:Value}' --output table
```
You need at least 1 vCPU (e.g. one `t3.micro`) available.

**Why the instance isn’t launching (Auto Scaling group):**  
Get your ASG name from the Beanstalk environment’s CloudFormation stack, or list ASGs:
```bash
aws autoscaling describe-auto-scaling-groups --region us-east-1 --query 'AutoScalingGroups[?contains(AutoScalingGroupName, `awseb`)].AutoScalingGroupName' --output text
```
Then check scaling activity for the failure reason:
```bash
aws autoscaling describe-scaling-activities --auto-scaling-group-name "ASG_NAME_HERE" --region us-east-1 --max-items 5 --query 'Activities[*].{Time:StartTime,StatusCode:StatusCode,StatusMessage:StatusMessage}' --output table
```
If you see **"The specified instance type is not eligible for Free Tier"**, the account is restricted to Free Tier–eligible types. Use **t3.micro** (or another Free Tier type) in `.ebextensions` (e.g. `InstanceType: t3.micro`) and redeploy.

**Free Tier–eligible instance types (example):**
```bash
aws ec2 describe-instance-types --filters "Name=free-tier-eligible,Values=true" --region us-east-1 --query 'InstanceTypes[*].InstanceType' --output text
```

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

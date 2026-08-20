# Chatlee.io Bulk Signup + Airdrop Automation

Automated bulk account creation on Chatlee.io with referral support and automatic airdrop task completion.

## Features

- ✅ Bulk account signup with email verification (OTP)
- ✅ Referral support (all accounts use the same referral link)
- ✅ Real Gmail disposable addresses via Emailnator (dotGmail/googleMail providers)
- ✅ Turnstile CAPTCHA via 2captcha (origin-validated; local solvers are rejected by Chatlee)
- ✅ Automatic OTP retrieval from Emailnator inbox
- ✅ Automatic airdrop task completion (onboarding + like posts + follow users) with reward claim
- ✅ HTTP proxy rotation with freshness probing (proxyscrape format)
- ✅ Incremental CSV output (accounts saved as created)
- ✅ Error handling with retry logic

## Setup

### 1. Install Dependencies

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Configure 2captcha API Key

Create `~/.agent/credentials/2captcha-api-key.env` (or export):

```bash
export TWOCAPTCHA_API_KEY=YOUR_2CAPTCHA_KEY
```

2captcha is REQUIRED — Chatlee validates Turnstile origin, so tokens from local
solvers (e.g. Waguri route-intercept) are rejected with `CAPTCHA verification failed`.

### 3. Proxy List (recommended)

Put HTTP proxies in `proxies.txt`, one per line, `user:pass@ip:port` format:

```
user:pass@proxy.example.com:3129
```

Chatlee rate-limits per IP (429 after ~1-2 registrations), so proxy rotation is
needed for bulk runs. Each proxy supports ~1-2 registrations before being burned.

## Usage

```bash
# Single account
python3 main.py --ref-url "https://chatlee.io/?inv=<BASE64_REF>" --count 1 --use-proxy

# Bulk with proxy rotation
python3 main.py --ref-url "https://chatlee.io/?inv=<BASE64_REF>" --count 50 --delay 3 --use-proxy
```

The `?inv=` parameter is base64 of the referrer's raw user ID. The script decodes
it automatically and sets the `invite` cookie.

## Output

Accounts are saved incrementally to `accounts.csv`:

```
email,password,login,user_id,ref_code,access_token,tasks_completed
```

## Notes

- **Emailnator recycling**: Emailnator recycles dot-variations of the same Gmail
  base (e.g. `a.b.c@gmail.com` and `abc@gmail.com` are the same Gmail account).
  Chatlee normalizes dots at registration, so recycled bases fail with
  "Email is already registered". The script tracks used bases from the CSV and
  retries with fresh emails.
- **Proxy burnout signal**: A burned proxy returns `400 Email is already registered`
  for ANY email (misleading error), not `429`. Probe proxies with the lightweight
  `check-email` endpoint (does NOT consume registration quota).
- **Waguri local solver does NOT work** for Chatlee (origin-bound managed Turnstile).
  Use 2captcha only.

## Files

| File | Purpose |
|------|---------|
| `main.py` | Main orchestrator |
| `api.py` | Chatlee.io API client |
| `solver.py` | Turnstile via 2captcha |
| `emailnator.py` | Emailnator disposable Gmail client |
| `proxy_pool.py` | HTTP proxy rotation + freshness probe |
| `config.json` | Config (2captcha URL, sitekey, retries) |

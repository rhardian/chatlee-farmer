# Chatlee.io Bulk Signup + Airdrop Automation

Automated bulk account creation on Chatlee.io with referral chain support and automatic airdrop task completion.

## Features

- ✅ Bulk account signup with email verification
- ✅ Referral chain: each account refers the next
- ✅ Turnstile CAPTCHA solving via Waguri solver
- ✅ **Emailnator.com integration for disposable emails**
- ✅ Automatic OTP retrieval from inbox
- ✅ Automatic airdrop task completion
- ✅ Incremental CSV output (accounts saved as they're created)
- ✅ Error handling with retry logic

## Setup

### 1. Install Dependencies

```bash
cd ~/scripts/chatlee-farmer
pip3 install -r requirements.txt
```

### 2. Configure Waguri Solver Token

Create `~/.agent/credentials/captcha-solver-token.txt` with your Waguri API token:

```bash
echo "YOUR_TOKEN_HERE" > ~/.agent/credentials/captcha-solver-token.txt
chmod 600 ~/.agent/credentials/captcha-solver-token.txt
```

## Usage

### Basic Usage

```bash
python3 main.py \
  --ref-url "https://chatlee.io/?inv=MzQ4NzAwNTQyNjMxMTM3Mjgw" \
  --count 10
```

### With Custom Delay

```bash
python3 main.py \
  --ref-url "https://chatlee.io/?inv=YOUR_REF_CODE" \
  --count 20 \
  --delay 5.0
```

### Parameters

- `--ref-url`: Referral URL with `?inv=` parameter (required)
- `--count`: Number of accounts to create (required)
- `--delay`: Seconds to wait between accounts (default: 3.0)

## How It Works

### 1. Email Generation (Emailnator.com)

For each account, the script:
1. Generates a fresh disposable email via Emailnator.com
2. Uses hybrid API + scraping approach for reliability
3. Polls inbox for OTP emails from Chatlee
4. Extracts 6-digit verification code

**No Gmail accounts needed** - fully autonomous using temporary emails.

### 2. Account Creation Flow

```
Generate Email → Check Availability → Solve Turnstile #1 →
Register Account → Wait for OTP → Solve Turnstile #2 →
Verify Email → Get User Info → Complete Tasks
```

### 3. Referral Chain

The script implements automatic referral chaining:

1. Account #1 is created with your provided referral code
2. Account #2 is created with Account #1's referral code
3. Account #3 is created with Account #2's referral code
4. ... and so on

This builds a referral tree under your initial account.

## Output

Results are saved incrementally to `accounts.csv`:

```csv
email,password,login,user_id,ref_code,access_token,tasks_completed
temp123@emailnator.com,SecurePass123!,temp123,348700542631137280,MzQ4NzAwNTQyNjMxMTM3Mjgw,eyJhbG...,3
temp456@emailnator.com,SecurePass123!,temp456,348700542631137281,MzQ4NzAwNTQyNjMxMTM3Mjgx,eyJhbG...,3
```

## API Endpoints

The script interacts with these Chatlee.io endpoints:

- `GET /api/auth/check-email` - Check email availability
- `GET /api/auth/check-login` - Check username availability
- `POST /api/auth/register` - Register new account
- `POST /api/auth/verify-email` - Verify email with OTP
- `GET /api/auth` - Get user info
- `GET /api/tasks` - List available tasks
- `POST /api/tasks/{id}/start` - Start a task
- `POST /api/users/onboarding` - Complete onboarding

## Error Handling

The script includes comprehensive error handling:

- **Turnstile timeout**: Retries 3x with 5s delay
- **OTP not received**: Skips account, logs error, continues
- **Task completion failed**: Logs error, continues to next task
- **Rate limit (HTTP 429)**: Exponential backoff (10s, 30s, 60s)
- **Email generation failed**: Retries with new email

## Troubleshooting

### OTP Not Received

1. Check Emailnator.com is accessible: `curl -I https://www.emailnator.com`
2. Increase `otp_timeout` in `config.json` (default: 60s)
3. Verify Chatlee is sending emails (check one account manually)

### Turnstile Solving Fails

1. Check Waguri solver token is valid
2. Verify solver is accessible: `curl https://waguri.vpnx.me/health`
3. Check solver has available balance
4. Increase retry count in `config.json`

### Email Generation Fails

1. Check if Emailnator.com has changed their UI/API
2. Update scraping selectors in `emailnator.py`
3. Consider alternative services (mail.tm, temp-mail.org)

### Rate Limiting

If you hit rate limits:

1. Increase `--delay` parameter (try 10-15 seconds)
2. Use fewer concurrent accounts
3. Add proxy rotation (future enhancement)

## Cost Estimate

Per account:
- **Turnstile solves**: 2 per account (register + verify)
- **Waguri cost**: ~$0.0005 per account (2 × $0.00025)
- **Emailnator**: Free (no API key needed)
- **Time**: ~45-60 seconds per account

For 100 accounts:
- **Total cost**: ~$0.05 (Turnstile solving only)
- **Total time**: ~75-100 minutes

## Architecture

```
main.py              # Entry point, orchestrates account creation
├── api.py           # Chatlee.io API client
├── solver.py        # Waguri Turnstile solver client
├── emailnator.py    # Emailnator.com disposable email client
├── config.json      # Configuration (URLs, timeouts, retry logic)
└── accounts.csv     # Output (generated accounts)
```

## Security Notes

- All passwords are set to `SecurePass123!` by default
- Access tokens are stored in plaintext CSV
- Keep `accounts.csv` secure (chmod 600)
- Disposable emails are public - don't use for sensitive data
- Don't commit credentials to git

## Future Enhancements

- [ ] Proxy rotation for rate limit avoidance
- [ ] Parallel account creation with threading
- [ ] Alternative captcha solver fallback (2captcha)
- [ ] Alternative email services (mail.tm, guerrillamail)
- [ ] More detailed task completion (like posts, follow users)
- [ ] Resume from last successful account
- [ ] Telegram notifications on completion
- [ ] Headless browser fallback if API changes

## Known Limitations

1. **Emailnator rate limits**: May block after many requests from same IP
2. **Turnstile difficulty**: Some sitekeys take 60+ seconds to solve
3. **Email delivery delay**: Chatlee emails may take 10-30s to arrive
4. **API changes**: Chatlee or Emailnator may update their APIs

## License

MIT

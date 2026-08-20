#!/usr/bin/env python3
"""
Chatlee.io bulk signup + airdrop automation with referral chain
Uses Emailnator.com for disposable emails and local Turnstile solver
"""
import argparse
import json
import csv
import time
import random
import base64
import re
import requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from api import ChatleeAPI
from solver import TurnstileSolver
from emailnator import EmailnatorClient


def load_config():
    """Load configuration from config.json"""
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError("config.json not found")
    return json.loads(config_path.read_text())


def extract_ref_from_url(url):
    """
    Extract referral code from URL
    
    Args:
        url: Referral URL like https://chatlee.io/?inv=MzQ4NzAwNTQyNjMxMTM3Mjgw
        
    Returns:
        str: Base64 encoded referral ID
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    if 'inv' in params:
        return params['inv'][0]
    
    raise ValueError("No 'inv' parameter found in URL")


def generate_account_data(email):
    """
    Generate account registration data
    
    Args:
        email: Email address
        
    Returns:
        dict: Account data with login, name, password
    """
    # Extract username from email (part before @)
    local_part = email.split('@')[0]
    
    # Generate variations - ensure <= 15 chars for login
    base = re.sub(r'[^a-zA-Z0-9]', '', local_part).lower()
    login = base[:15]
    
    # Ensure login is at least 3 chars
    if len(login) < 3:
        import random
        login = login + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=3))
    
    name = local_part.title()[:20]   # Capitalize first letter
    password = "SecurePass123!"      # Standard password for all accounts
    
    return {
        "login": login,
        "name": name,
        "password": password,
        "email": email
    }


def create_account(api, solver, email_client, account_data, ref_code, config, proxy_str=None):
    """
    Create a single Chatlee account
    
    Args:
        api: ChatleeAPI instance
        solver: TurnstileSolver instance
        email_client: EmailnatorClient instance
        account_data: Account registration data
        ref_code: Referral code for this account
        config: Configuration dict
        proxy_str: Optional proxy string
        
    Returns:
        dict: Account result with tokens and user info
    """
    email = account_data["email"]
    login = account_data["login"]
    
    print(f"\n[{email}] Starting signup...")
    
    # Set invite cookie
    api.set_invite_cookie(ref_code)
    
    # Check email availability (also check base without dots - Gmail treats as same)
    print(f"  Checking email availability...")
    try:
        base_email = email.split('@')[0].replace('.', '') + '@gmail.com'
        email_check = api.check_email(email)
        if email_check.get("exists"):
            print(f"  ✗ Email already exists: {email}")
            return None
        # Check base variant too (emailnator recycles dot-variations of same Gmail)
        if base_email != email:
            base_check = api.check_email(base_email)
            if base_check.get("exists"):
                print(f"  ✗ Base email already exists: {base_email}")
                return None
    except Exception as e:
        print(f"  ⚠ Email check failed (continuing): {e}")
    
    # Check username availability
    print(f"  Checking username availability...")
    try:
        login_check = api.check_login(login)
        if not login_check.get("available", True):
            # Try variations
            import random
            suffix = ''.join(random.choices('0123456789', k=3))
            login = login[:12] + suffix
            account_data["login"] = login
            print(f"  Username taken, using: {login}")
    except Exception as e:
        print(f"  ⚠ Username check failed (continuing): {e}")
    
    # Solve Turnstile for registration
    print(f"  Solving Turnstile (register)...")
    turnstile_token_1 = solver.solve(
        sitekey=config["chatlee_api"]["sitekey"],
        url=config["chatlee_api"]["base_url"] + "/sign-in"
    )
    
    # Register account
    print(f"  Registering account...")
    register_resp = api.register(
        login=login,
        email=email,
        password=account_data["password"],
        name=account_data["name"],
        ref_code=ref_code,
        turnstile_token=turnstile_token_1
    )
    
    if register_resp.get("status") != "pending":
        # Email taken - try with fresh token? No, return None for retry with new email
        print(f"  ✗ Register failed: {register_resp.get('message', register_resp)}")
        return None
    
    # Wait for OTP email
    print(f"  Waiting for OTP email...")
    try:
        otp_code = email_client.wait_for_otp(
            email=email,
            timeout=config.get("otp_timeout", 120)
        )
        print(f"  OTP received: {otp_code}")
    except TimeoutError as e:
        print(f"  ERROR: {e}")
        return None
    
    # Solve Turnstile for verification
    print(f"  Solving Turnstile (verify)...")
    turnstile_token_2 = solver.solve(
        sitekey=config["chatlee_api"]["sitekey"],
        url=config["chatlee_api"]["base_url"] + "/sign-in"
    )
    
    # Verify email with retry on failure
    print(f"  Verifying email...")
    verify_resp = None
    for verify_attempt in range(2):
        try:
            verify_resp = api.verify_email(
                email=email,
                code=otp_code,
                turnstile_token=turnstile_token_2
            )
            break
        except Exception as e:
            print(f"  ⚠ Verify failed (attempt {verify_attempt + 1}): {e}")
            if verify_attempt == 0:
                print(f"  Solving fresh Turnstile for retry...")
                turnstile_token_2 = solver.solve(
                    sitekey=config["chatlee_api"]["sitekey"],
                    url=config["chatlee_api"]["base_url"] + "/sign-in"
                )
            else:
                return None
    
    if not verify_resp or verify_resp.get("status") != "success":
        print(f"  ✗ Verification failed: {verify_resp}")
        return None
    
    # Get user info for referral code
    print(f"  Fetching user info...")
    user_info = api.get_user_info()
    user = user_info.get("user", {})
    user_id = user.get("id") or user_info.get("id") or user_info.get("user_id")
    
    if not user_id and verify_resp:
        # verify-email response also has user info
        user_id = verify_resp.get("user", {}).get("id")
    
    # Generate referral code - raw user ID (numeric string)
    my_ref_code = str(user_id) if user_id else ""
    
    # Complete tasks
    tasks_completed = 0
    if config.get("task_completion_enabled", True):
        print(f"  Completing tasks...")
        try:
            tasks_completed = api.complete_tasks()
        except Exception as e:
            print(f"  ✗ Task completion error: {e}")
    
    # Extract access token from cookies
    access_token = api.session.cookies.get("accessToken", "")
    
    print(f"  SUCCESS: {tasks_completed} tasks completed")
    
    return {
        "email": email,
        "password": account_data["password"],
        "login": login,
        "user_id": user_id,
        "ref_code": my_ref_code,
        "access_token": access_token,
        "tasks_completed": tasks_completed
    }


def save_account(csv_path, account):
    """
    Append account to CSV file
    
    Args:
        csv_path: Path to accounts.csv
        account: Account data dict
    """
    file_exists = csv_path.exists()
    
    with open(csv_path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "email", "password", "login", "user_id", "ref_code", "access_token", "tasks_completed"
        ])
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(account)


def main():
    parser = argparse.ArgumentParser(description="Chatlee.io bulk signup automation")
    parser.add_argument("--ref-url", required=True, help="Referral URL (e.g., https://chatlee.io/?inv=...)")
    parser.add_argument("--count", type=int, required=True, help="Number of accounts to create")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between accounts (seconds)")
    parser.add_argument("--use-proxy", action="store_true", help="Rotate HTTP proxy per account (proxies.txt)")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Extract initial referral code from URL
    initial_ref_code = extract_ref_from_url(args.ref_url)
    print(f"Initial referral code: {initial_ref_code}")
    
    # Initialize components
    solver = TurnstileSolver(
        base_url=config["captcha_solver"]["url"],
        timeout=config["captcha_solver"]["timeout"]
    )
    
    email_client = EmailnatorClient()
    
    # Optional proxy rotation
    proxy_pool = None
    if args.use_proxy:
        from proxy_pool import ProxyPool
        proxy_pool = ProxyPool(Path(__file__).parent / "proxies.txt")
        print("HTTP proxy rotation enabled")
    
    # Output CSV path
    csv_path = Path(__file__).parent / config["accounts_output"]
    
    print(f"\nStarting bulk signup: {args.count} accounts")
    print(f"Output: {csv_path}")
    print("=" * 60)
    
    # Referral chain: account 1 uses initial ref, account 2 uses account 1's ref, etc.
    current_ref_code = initial_ref_code
    
    for i in range(args.count):
        try:
            # Find fresh proxy (not rate-limited by Chatlee)
            proxy_str = None
            if proxy_pool:
                print(f"\n[Account {i+1}/{args.count}] Finding fresh proxy...")
                proxy_str = proxy_pool.find_fresh_proxy(config["chatlee_api"]["base_url"])
                print(f"  Fresh proxy: {proxy_str}")
            
            result = None
            # Retry with fresh email up to 5 times (emailnator may recycle used emails)
            for email_attempt in range(5):
                # Generate new disposable email
                print(f"  Generating disposable email...")
                email = email_client.generate_email()
                print(f"  Generated: {email}")
                
                # Create API client (fresh session per account)
                api = ChatleeAPI(config["chatlee_api"]["base_url"])
                
                # Route API through proxy if enabled
                if proxy_str:
                    api.session.proxies = proxy_pool.get_proxy_dict(proxy_str)
                
                # Generate account data
                account_data = generate_account_data(email)
                
                # Create account
                result = create_account(
                    api=api,
                    solver=solver,
                    email_client=email_client,
                    account_data=account_data,
                    ref_code=current_ref_code,
                    config=config,
                    proxy_str=proxy_str
                )
                
                if result:
                    break
                
                print(f"  ⚠ Attempt {email_attempt + 1} failed, trying new email...")
            
            if result:
                # Save immediately
                save_account(csv_path, result)
                
                # Update referral code for next account
                current_ref_code = result["ref_code"]
                print(f"  → Next account will use ref: {current_ref_code}")
            else:
                print(f"  ✗ FAILED: Account creation failed after 3 attempts")
        
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        # Delay before next account
        if i < args.count - 1:
            delay = args.delay + random.uniform(0, 2)
            print(f"\nWaiting {delay:.1f}s before next account...")
            time.sleep(delay)
    
    print("\n" + "=" * 60)
    print(f"Bulk signup completed. Results saved to: {csv_path}")


if __name__ == "__main__":
    main()

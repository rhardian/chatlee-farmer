"""
Turnstile CAPTCHA solver via 2captcha.com (origin-validated tokens)
Chatlee.io validates Turnstile origin, so local solver tokens are rejected.
Supports optional proxy for IP matching.
"""
import requests
import time
import os
from pathlib import Path


class TurnstileSolver:
    def __init__(self, base_url="https://2captcha.com", timeout=180):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # Load API key
        key_path = Path("~/.agent/credentials/2captcha-api-key.env").expanduser()
        self.api_key = ""
        for line in key_path.read_text().splitlines():
            if line.startswith("TWOCAPTCHA_API_KEY="):
                self.api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
        
        if not self.api_key:
            raise FileNotFoundError("2captcha API key not found")
    
    def solve(self, sitekey, url, max_retries=3, retry_delay=5, proxy=None):
        """
        Solve Turnstile captcha via 2captcha
        
        Args:
            sitekey: Turnstile sitekey
            url: Page URL where captcha is embedded
            max_retries: Number of retry attempts
            retry_delay: Seconds to wait between retries
            proxy: Proxy string (login:pass@ip:port) for IP matching
            
        Returns:
            str: Turnstile token
            
        Raises:
            Exception: If solving fails after all retries
        """
        for attempt in range(max_retries):
            try:
                # Submit task
                data = {
                    "key": self.api_key,
                    "method": "turnstile",
                    "sitekey": sitekey,
                    "pageurl": url,
                    "json": "1"
                }
                if proxy:
                    data["proxy"] = proxy
                    data["proxytype"] = "SOCKS5"
                
                submit_resp = requests.post(
                    f"{self.base_url}/in.php",
                    data=data,
                    timeout=30
                )
                
                result = submit_resp.json()
                if result.get("status") != 1:
                    raise Exception(f"Submit failed: {result.get('request')}")
                
                task_id = result["request"]
                
                # Poll for result
                poll_start = time.time()
                while time.time() - poll_start < self.timeout:
                    time.sleep(5)
                    
                    poll_resp = requests.get(
                        f"{self.base_url}/res.php",
                        params={
                            "key": self.api_key,
                            "action": "get",
                            "id": task_id,
                            "json": "1"
                        },
                        timeout=30
                    )
                    
                    res = poll_resp.json()
                    if res.get("status") == 1:
                        return res["request"]
                    elif "CAPCHA_NOT_READY" in res.get("request", ""):
                        continue
                    else:
                        raise Exception(f"Solver error: {res.get('request')}")
                
                raise TimeoutError(f"Solver timeout after {self.timeout}s")
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  Turnstile solve failed (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Turnstile solving failed after {max_retries} attempts: {e}")

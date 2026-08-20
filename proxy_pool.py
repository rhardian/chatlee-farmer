"""
Proxy pool client for IP rotation (HTTP proxies from proxyscrape premium)
"""
import json
import time
import random
import requests
from pathlib import Path


class ProxyPool:
    def __init__(self, proxy_file=None):
        self.proxies = []
        self.index = 0
        self.current = None
        
        if proxy_file:
            self.load(proxy_file)
    
    def load(self, proxy_file):
        """Load proxies from file (user:pass@ip:port format, one per line)"""
        path = Path(proxy_file).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Proxy file not found: {proxy_file}")
        
        self.proxies = [line.strip() for line in path.read_text().splitlines() if line.strip() and '@' in line]
        random.shuffle(self.proxies)
        print(f"  Loaded {len(self.proxies)} proxies")
    
    def next(self):
        """Get next proxy (round-robin)"""
        if not self.proxies:
            return None
        proxy = self.proxies[self.index % len(self.proxies)]
        self.index += 1
        self.current = proxy
        return proxy
    
    def get_proxy_dict(self, proxy_str):
        """Convert user:pass@ip:port to requests proxy dict"""
        return {
            "http": f"http://{proxy_str}",
            "https": f"http://{proxy_str}"
        }
    
    def test(self, proxy_str, timeout=10):
        """Test if proxy works by checking egress IP"""
        try:
            proxies = self.get_proxy_dict(proxy_str)
            r = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=timeout)
            if r.status_code == 200:
                return r.json().get("ip")
        except Exception:
            pass
        return None
    
    def find_fresh_proxy(self, chatlee_base, max_attempts=20, timeout=15):
        """
        Find a proxy that:
        1. Works (egress OK)
        2. Can reach Chatlee API (not blocked)
        
        IMPORTANT: does NOT burn the proxy by POSTing register — that consumes
        the per-IP registration quota. Only uses lightweight check-email.
        
        Returns:
            str: Fresh proxy string or None
        """
        for _ in range(max_attempts):
            proxy = self.next()
            if not proxy:
                return None
            
            ip = self.test(proxy)
            if not ip:
                continue
            
            # Lightweight probe: check-email with random unique email.
            # 200 = proxy can reach Chatlee and is likely fresh.
            # 429 = rate-limited, 403/blocked = burned.
            try:
                s = requests.Session()
                s.proxies = self.get_proxy_dict(proxy)
                s.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                })
                
                import random
                import string
                uniq = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
                r = s.get(
                    f"{chatlee_base}/api/auth/check-email",
                    params={"email": f"probe{uniq}@gmail.com"},
                    timeout=timeout
                )
                
                if r.status_code == 200:
                    return proxy
                print(f"  ⚠ Proxy {proxy.split('@')[1]} blocked (HTTP {r.status_code})")
            except Exception as e:
                print(f"  ⚠ Proxy {proxy.split('@')[1]} error: {str(e)[:50]}")
        
        return None
    
    def next_working(self, max_attempts=5):
        """
        Get next working proxy (tests egress)
        
        Returns:
            tuple: (proxy_str, ip) or (None, None) if none work
        """
        for _ in range(max_attempts):
            proxy = self.next()
            if not proxy:
                return None, None
            ip = self.test(proxy)
            if ip:
                return proxy, ip
            print(f"  ⚠ Proxy dead: {proxy}")
        return None, None
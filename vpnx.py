"""
VPNX SOCKS5 proxy pool client for IP rotation
"""
import json
import time
import requests


class VPNXClient:
    def __init__(self, api="http://127.0.0.1:8000", token="decedef2c17fae36c9d771ccd5ba7f13",
                 proxy_host="127.0.0.1", proxy_port="1080",
                 username="vpnx14bebb30", password="c5e27f2e60793d85f3716798"):
        self.api = api.rstrip('/')
        self.token = token
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.username = username
        self.password = password
        self.proxy_url = f"socks5h://{username}:{password}@{proxy_host}:{proxy_port}"
        self.current_ip = None
    
    def get_status(self):
        """Get current VPNX status"""
        r = requests.get(f"{self.api}/status", headers={"Authorization": f"Bearer {self.token}"}, timeout=15)
        return r.json()
    
    def rotate(self):
        """Rotate to a new VPN server"""
        r = requests.post(f"{self.api}/rotate", headers={"Authorization": f"Bearer {self.token}"}, timeout=90)
        return r.json()
    
    def get_session(self):
        """Get requests session routed through VPNX proxy"""
        s = requests.Session()
        s.proxies = {
            "http": self.proxy_url,
            "https": self.proxy_url
        }
        return s
    
    def ensure_fresh_ip(self):
        """Rotate proxy to get a fresh IP. Returns new IP string."""
        res = self.rotate()
        time.sleep(3)
        try:
            status = self.get_status()
            ip = status.get("vpn", {}).get("ip") or status.get("ip", "?")
        except:
            ip = "?"
        self.current_ip = ip
        return ip
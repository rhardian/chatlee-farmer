"""
Emailnator.com disposable email client for OTP retrieval
Produces real Gmail addresses (dotGmail/googleMail providers).
"""
import requests
import time
import re
from urllib.parse import unquote


class EmailnatorClient:
    def __init__(self):
        self.base_url = "https://www.emailnator.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            "Origin": "https://www.emailnator.com",
            "Referer": "https://www.emailnator.com/",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json"
        })
        self.email = None
    
    def _init_csrf(self):
        """Visit homepage and set XSRF token header"""
        self.session.get(f"{self.base_url}/", timeout=15)
        xsrf = self.session.cookies.get("XSRF-TOKEN")
        if xsrf:
            self.session.headers.update({"X-XSRF-TOKEN": unquote(xsrf)})
            return True
        return False
    
    def generate_email(self, provider="dotGmail"):
        """
        Generate a new disposable Gmail address
        
        Args:
            provider: "dotGmail" | "googleMail" | both as list
            
        Returns:
            str: Generated email address
        """
        if not self.session.headers.get("X-XSRF-TOKEN"):
            self._init_csrf()
        
        payload = {"email": [provider]}
        resp = self.session.post(
            f"{self.base_url}/generate-email",
            json=payload,
            timeout=15
        )
        
        if resp.status_code != 200:
            raise Exception(f"Email generation failed: HTTP {resp.status_code}")
        
        data = resp.json()
        emails = data.get("email", [])
        if not emails:
            raise Exception("No email in response")
        
        self.email = emails[0]
        return self.email
    
    def get_messages(self, email=None):
        """
        Get inbox messages
        
        Returns:
            list: List of message dicts with messageID, from, subject, time
        """
        email = email or self.email
        if not email:
            return []
        
        if not self.session.headers.get("X-XSRF-TOKEN"):
            self._init_csrf()
        
        resp = self.session.post(
            f"{self.base_url}/message-list",
            json={"email": email},
            timeout=15
        )
        
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        return data.get("messageData", [])
    
    def get_message_content(self, message_id, email=None):
        """
        Get full message content
        
        Args:
            message_id: Message ID
            email: Email address
            
        Returns:
            str: Message body text
        """
        email = email or self.email
        if not email:
            return ""
        
        if not self.session.headers.get("X-XSRF-TOKEN"):
            self._init_csrf()
        
        resp = self.session.post(
            f"{self.base_url}/message-list",
            json={"email": email, "messageID": message_id},
            timeout=15
        )
        
        if resp.status_code != 200:
            return ""
        
        return resp.text
    
    def wait_for_otp(self, email, timeout=120, poll_interval=5):
        """
        Wait for OTP code from Chatlee verification email
        
        Args:
            email: Email address to monitor
            timeout: Max seconds to wait
            poll_interval: Seconds between checks
            
        Returns:
            str: 6-digit OTP code
            
        Raises:
            TimeoutError: If OTP not received within timeout
        """
        self.email = email
        start_time = time.time()
        
        print(f"  Waiting for OTP on {email} (timeout: {timeout}s)...")
        
        seen_ids = set()
        
        while time.time() - start_time < timeout:
            try:
                messages = self.get_messages(email)
                
                for msg in messages:
                    msg_id = msg.get("messageID", "")
                    if not msg_id or msg_id in seen_ids or msg_id == "ADSVPN":
                        continue
                    
                    seen_ids.add(msg_id)
                    
                    subject = msg.get("subject", "").lower()
                    sender = msg.get("from", "").lower()
                    
                    # Look for Chatlee email
                    if ("chatlee" in sender or "chatlee" in subject or 
                        "verification" in subject or "verify" in subject or 
                        "code" in subject or "otp" in subject):
                        
                        content = self.get_message_content(msg_id, email)
                        
                        # Extract 6-digit code
                        match = re.search(r'\b(\d{6})\b', content)
                        if match:
                            otp = match.group(1)
                            print(f"  ✓ OTP received: {otp}")
                            return otp
            except Exception as e:
                print(f"  Poll error (retrying): {e}")
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"OTP not received within {timeout}s")

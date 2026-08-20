"""
Chatlee.io API client
"""
import requests
import time
import json
from urllib.parse import urlencode


class ChatleeAPI:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": base_url,
            "Referer": f"{base_url}/sign-in"
        })
    
    def set_invite_cookie(self, ref_code):
        """
        Set invite cookie from referral ID (raw user id)
        
        Args:
            ref_code: Raw user ID (numeric string) for invite cookie
        """
        # ref_code might be base64-encoded from URL query; decode if needed
        decoded = ref_code
        try:
            import base64
            raw = base64.b64decode(ref_code + '=' * (-len(ref_code) % 4)).decode()
            if raw.isdigit():
                decoded = raw
        except Exception:
            pass
        self.session.cookies.set("invite", decoded, domain="chatlee.io")
    
    def check_email(self, email):
        """
        Check if email is available
        
        Returns:
            dict: {"exists": bool}
        """
        response = self.session.get(
            f"{self.base_url}/api/auth/check-email",
            params={"email": email}
        )
        response.raise_for_status()
        return response.json()
    
    def check_login(self, username):
        """
        Check if username is available
        
        Returns:
            dict: {"available": bool}
        """
        response = self.session.get(
            f"{self.base_url}/api/auth/check-login",
            params={"login": username}
        )
        response.raise_for_status()
        return response.json()
    
    def register(self, login, email, password, name, ref_code, turnstile_token):
        """
        Register new account
        
        Returns:
            dict: Response with deviceId and pending_verification cookies
        """
        payload = {
            "login": login,
            "email": email,
            "password": password,
            "password2": password,
            "name": name,
            "ref": None,
            "turnstileToken": turnstile_token
        }
        
        response = self.session.post(
            f"{self.base_url}/api/auth/register",
            json=payload
        )
        
        # Return parsed JSON for both success and error (caller handles status)
        try:
            return response.json()
        except Exception:
            return {"status": "error", "message": f"HTTP {response.status_code}: {response.text[:200]}"}
    
    def verify_email(self, email, code, turnstile_token):
        """
        Verify email with OTP code
        
        Returns:
            dict: Response with user info (id for referral)
        """
        payload = {
            "email": email,
            "code": code,
            "turnstileToken": turnstile_token
        }
        
        response = self.session.post(
            f"{self.base_url}/api/auth/verify-email",
            json=payload
        )
        response.raise_for_status()
        
        return response.json()
    
    def get_user_info(self):
        """
        Get current user info (requires accessToken cookie)
        
        Returns:
            dict: User info including id for referral
        """
        response = self.session.get(f"{self.base_url}/api/auth")
        response.raise_for_status()
        return response.json()
    
    def get_tasks(self):
        """
        Get available airdrop tasks
        
        Returns:
            list: Available tasks
        """
        response = self.session.get(
            f"{self.base_url}/api/tasks",
            params={"page": 1, "count": 50}
        )
        response.raise_for_status()
        data = response.json()
        
        # Handle different response shapes
        if isinstance(data, dict):
            inner = data.get("data", data)
            if isinstance(inner, dict):
                return inner.get("data", [])
            if isinstance(inner, list):
                return inner
        elif isinstance(data, list):
            return data
        return []
    
    def start_task(self, task_id):
        """
        Start a task
        
        Returns:
            dict: Task start response
        """
        response = self.session.post(f"{self.base_url}/api/tasks/{task_id}/start")
        response.raise_for_status()
        return response.json()
    
    def complete_onboarding(self):
        """
        Complete onboarding task
        
        Returns:
            dict: Onboarding completion response
        """
        response = self.session.post(f"{self.base_url}/api/users/onboarding", json={})
        response.raise_for_status()
        return response.json()
    
    def like_post(self, post_id):
        """
        Like a post
        
        Args:
            post_id: Post ID to like
            
        Returns:
            dict: Like response
        """
        response = self.session.post(
            f"{self.base_url}/api/posts/{post_id}/like",
            json={}
        )
        response.raise_for_status()
        return response.json()
    
    def send_post_views(self, post_ids):
        """
        Send post views (shows post content + view tracking)
        
        Args:
            post_ids: List of post IDs
            
        Returns:
            dict: Post content with view tracking
        """
        response = self.session.post(
            f"{self.base_url}/api/posts/views",
            json={"postIds": post_ids}
        )
        response.raise_for_status()
        return response.json()
    
    def follow_user(self, user_id):
        """
        Follow a user
        
        Args:
            user_id: User ID to follow
            
        Returns:
            dict: Follow response
        """
        response = self.session.post(
            f"{self.base_url}/api/users/{user_id}/follow",
            json={"follow": True}
        )
        response.raise_for_status()
        return response.json()
    
    def get_feed(self):
        """
        Get feed posts with user ids for following/liking
        
        Returns:
            list: Feed posts
        """
        response = self.session.get(f"{self.base_url}/api/feed")
        response.raise_for_status()
        data = response.json()
        return data.get("posts", [])
    
    def complete_tasks(self, feed=None):
        """
        Complete available internal tasks (like/follow)
        
        Args:
            feed: Pre-fetched feed (optional)
            
        Returns:
            int: Number of tasks completed
        """
        tasks_completed = 0
        
        try:
            # Complete onboarding first
            self.complete_onboarding()
            tasks_completed += 1
            print(f"    ✓ Onboarding completed")
        except Exception as e:
            print(f"    ✗ Onboarding failed: {e}")
        
        # Get tasks list
        try:
            tasks = self.get_tasks()
            print(f"    Tasks fetched: {len(tasks)}")
            
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                    
                task_id = task.get("id")
                task_type = task.get("type", "")
                target = task.get("target", 1)
                status = task.get("status", 0)
                
                # Task 36: Invite a friend - auto-completes when referral joins
                # Task 67/68: Steam wishlist - needs actual Steam, skip
                if task_type in ("add_wishlist", "referral"):
                    continue
                
                if task_type == "like" and status == 0:
                    # Need to like N posts
                    likes_needed = target
                    feed_posts = self.get_feed()
                    liked = 0
                    for post in feed_posts:
                        if liked >= likes_needed:
                            break
                        post_id = post.get("id")
                        if not post_id:
                            continue
                        try:
                            self.like_post(post_id)
                            liked += 1
                            print(f"    ✓ Liked post {post_id}")
                            time.sleep(0.5)
                        except Exception as e:
                            print(f"    ✗ Like failed: {e}")
                            continue
                    if liked >= likes_needed:
                        tasks_completed += 1
                
                elif task_type == "follow" and status == 0:
                    # Need to follow N users
                    follows_needed = target
                    feed_posts = self.get_feed()
                    user_ids = set()
                    for post in feed_posts:
                        uid = post.get("user_id")
                        if uid and uid != "0":
                            user_ids.add(uid)
                    
                    followed = 0
                    for uid in list(user_ids)[:follows_needed + 5]:
                        if followed >= follows_needed:
                            break
                        try:
                            self.follow_user(uid)
                            followed += 1
                            print(f"    ✓ Followed user {uid}")
                            time.sleep(0.5)
                        except Exception as e:
                            print(f"    ✗ Follow failed: {e}")
                            continue
                    if followed >= follows_needed:
                        tasks_completed += 1
                
                elif task_type == "onboarding":
                    try:
                        self.complete_onboarding()
                        tasks_completed += 1
                        print(f"    ✓ Onboarding task {task_id} completed")
                    except Exception as e:
                        print(f"    ✗ Onboarding task failed: {e}")
            
        except Exception as e:
            print(f"    ✗ Failed to fetch tasks: {e}")
        
        return tasks_completed
    
    def handle_rate_limit(self, backoff_schedule):
        """
        Handle rate limiting with exponential backoff
        
        Args:
            backoff_schedule: List of seconds to wait [10, 30, 60]
        """
        for delay in backoff_schedule:
            print(f"  Rate limited, waiting {delay}s...")
            time.sleep(delay)
            return
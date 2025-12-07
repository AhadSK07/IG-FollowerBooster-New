import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import json
import os
from urllib.parse import urlparse

# --- CONFIGURATION ---

# Time to wait (in seconds) after a successful follower send
# Set to 0 if you want to close immediately, or 120 for safety.
POST_TASK_WAIT = 120 

# Time to wait (in seconds) between switching websites
# (Min, Max) range for random sleep
INTER_SITE_DELAY = (30, 45)

WEBSITES = [
    "https://instamoda.org/login",
    "https://takipcitime.com/login",
    "https://takipcikrali.com/login",
    "https://takipcimx.net/login",
    "https://takipciking.com/member",
    "https://birtakipci.com/member",
    "https://medyahizmeti.com/member",
    "https://fastfollow.in/member",
    "https://takipcigir.com/login",
    "https://bayitakipci.com/memberlogin"
]

TARGET_USER = "mr_faiz__1127"

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def setup_accounts():
    """
    Loads accounts with a priority fallback:
    1. Environment Variable (GitHub Secrets)
    2. Local File (accounts.json)
    """
    
    # PRIORITY 1: Check Environment Variable
    env_data = os.environ.get("ACCOUNTS_JSON")
    
    if env_data:
        print(">> [SOURCE] Found 'ACCOUNTS_JSON' in environment variables.")
        try:
            return json.loads(env_data)
        except json.JSONDecodeError as e:
            logging.error(f"CRITICAL: Environment variable 'ACCOUNTS_JSON' has invalid JSON syntax: {e}")
            return []

    # PRIORITY 2: Check Local File (Fallback)
    print(">> [SOURCE] Environment variable not found. Checking for local 'accounts.json' file...")
    
    if os.path.exists("accounts.json"):
        try:
            with open("accounts.json", "r") as f:
                accounts = json.load(f)
                print(">> [SOURCE] Successfully loaded local 'accounts.json'.")
                return accounts
        except json.JSONDecodeError as e:
            logging.error(f"CRITICAL: Local file 'accounts.json' has invalid JSON syntax: {e}")
            return []
        except Exception as e:
            logging.error(f"CRITICAL: Error reading local file: {e}")
            return []

    # FAILURE: Neither source worked
    logging.error("CRITICAL: No accounts found! Please set 'ACCOUNTS_JSON' secret or create 'accounts.json'.")
    return []

class PanelBot:
    def __init__(self, full_login_url, username, password, target):
        self.login_url = full_login_url
        parsed = urlparse(full_login_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.username = username
        self.password = password
        self.target = target
        self.session = requests.Session()
        self.session.headers.update({
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
        })

    def log(self, message, level="info"):
        full_msg = f"[{self.base_url}] [{self.username}] {message}"
        if level == "error":
            logging.error(full_msg)
        else:
            logging.info(full_msg)

    def login(self):
        data = {'username': self.username, 'password': self.password}
        try:
            self.log(f"Attempting login at {self.login_url}...")
            response = self.session.post(self.login_url, data=data, timeout=30)
            try:
                result = response.json()
            except ValueError:
                self.log("Login failed: Non-JSON response received.", "error")
                return False

            if 'returnUrl' in result:
                self.log("Login successful.")
                return True
            elif 'error' in result:
                self.log(f"Login failed: {result['error']}", "error")
                return False
            else:
                self.log("Login failed: Unknown response format.", "error")
                return False
        except requests.RequestException as e:
            self.log(f"Connection error during login: {str(e)}", "error")
            return False

    def get_credits(self):
        try:
            tools_url = f"{self.base_url}/tools"
            response = self.session.get(tools_url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            credit_element = soup.find(id="takipKrediCount")
            if credit_element:
                try:
                    return int(credit_element.text.strip())
                except ValueError:
                    return 0
            return 0
        except Exception:
            return 0

    def send_followers(self, credit_amount):
        if credit_amount <= 0:
            return False
        try:
            find_user_url = f"{self.base_url}/tools/send-follower?formType=findUserID"
            response_find = self.session.post(find_user_url, data={'username': self.target}, timeout=30)
            try:
                user_id = response_find.url.split("/")[-1]
            except Exception:
                self.log("Failed to extract User ID.", "error")
                return False

            self.log(f"Target ID found: {user_id}. Sending {credit_amount} followers...")
            send_url = f"{response_find.url}?formType=send"
            send_data = {'adet': credit_amount, 'userID': user_id, 'userName': self.target}
            
            response_send = self.session.post(send_url, data=send_data, timeout=30)
            result = response_send.json()

            if result.get('status') == 'success':
                self.log(f"SUCCESS: Sent {credit_amount} followers.")
                return True
            else:
                self.log(f"FAILED to send: {result.get('message')}", "error")
                return False
        except Exception as e:
            self.log(f"Error sending: {e}", "error")
            return False
            
    def close_session(self):
        try:
            self.session.close()
        except Exception:
            pass

    def run(self):
        """
        Returns:
            bool: True if followers were successfully sent, False otherwise.
        """
        if self.login():
            credits = self.get_credits()
            self.log(f"Credits available: {credits}")
            if credits > 0:
                success = self.send_followers(credits)
                return success
            else:
                self.log("Skipping sending due to 0 credits.")
                return False
        else:
            self.log("Skipping operations due to login failure.")
            return False

# --- ORCHESTRATION ---

def main():
    print(f"Starting AUTOMATION for target: {TARGET_USER}")
    
    # LOAD ACCOUNTS (ENV -> LOCAL FALLBACK)
    accounts = setup_accounts()
    
    if not accounts:
        print("!! No accounts loaded. Exiting.")
        return

    print(f"Loaded {len(accounts)} accounts.")

    for account in accounts:
        current_user = account.get('username')
        password = account.get('password')
        
        if not current_user or not password:
            logging.error(f"Account entry missing username or password: {account}")
            continue

        print(f"\n==================================================")
        print(f" LOGGING IN WITH ACCOUNT: {current_user}")
        print(f"==================================================")

        for i, site_url in enumerate(WEBSITES):
            print(f"\n--- Site {i+1}/{len(WEBSITES)}: {site_url} ---")
            bot = None
            try:
                bot = PanelBot(site_url, current_user, password, TARGET_USER)
                success = bot.run()
                
                if success:
                    print(f"[{site_url}] Operation succeeded.")
                    if POST_TASK_WAIT > 0:
                        print(f">> Waiting {POST_TASK_WAIT}s for completion...")
                        time.sleep(POST_TASK_WAIT)
                else:
                    print(f"[{site_url}] Operation failed or skipped.")
            
            except Exception as e:
                logging.error(f"[{site_url}] Unexpected error: {e}")
            
            finally:
                if bot:
                    bot.close_session()

            # Smart delay between websites (unless it's the last one
            if i < len(WEBSITES) - 1:
                delay = random.uniform(INTER_SITE_DELAY[0], INTER_SITE_DELAY[1])
                print(f">> Cooldown: Waiting {delay:.2f} seconds...")
                time.sleep(delay)

    print("\nAll tasks completed successfully.")

if __name__ == "__main__":
    main()

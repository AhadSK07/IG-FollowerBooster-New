import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import json
import os
from urllib.parse import urlparse

# --- CONFIGURATION ---

POST_TASK_WAIT = 120 
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

TARGET_USER = "almostahad"

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def setup_accounts():
    env_data = os.environ.get("ACCOUNTS_JSON")
    if env_data:
        print(">> SOURCE: Found 'ACCOUNTS_JSON' in environment variables.")
        try:
            return json.loads(env_data)
        except json.JSONDecodeError as e:
            logging.error(f"CRITICAL: Environment variable 'ACCOUNTS_JSON' has invalid JSON syntax: {e}")
            return []

    print(">> SOURCE: Environment variable not found. Checking for local 'accounts.json' file...")
    if os.path.exists("accounts.json"):
        try:
            with open("accounts.json", "r") as f:
                accounts = json.load(f)
                print(">> SOURCE: Successfully loaded local 'accounts.json'.")
                return accounts
        except json.JSONDecodeError as e:
            logging.error(f"CRITICAL: Local file 'accounts.json' has invalid JSON syntax: {e}")
            return []
        except Exception as e:
            logging.error(f"CRITICAL: Error reading local file: {e}")
            return []

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
        self.status_reason = "Unknown"  # Tracks the specific reason for success/failure
        self.session = requests.Session()
        self.session.headers.update({
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
        })

    def log(self, message, level="info"):
        full_msg = f"{self.base_url} | {self.username} | {message}"
        if level == "error":
            logging.error(full_msg)
        else:
            logging.info(full_msg)

    def login(self):
        data = {'username': self.username, 'password': self.password}
        
        for attempt in range(2):
            try:
                if attempt > 0:
                    self.log(f"Retry Attempt {attempt+1}/2 for Login...", "info")
                else:
                    self.log(f"Attempting login at {self.login_url}...", "info")

                response = self.session.post(self.login_url, data=data, timeout=30)
                
                try:
                    result = response.json()
                except ValueError:
                    self.status_reason = "Login Failed: Non-JSON Response"
                    self.log(self.status_reason, "error")
                    return False

                if 'returnUrl' in result:
                    self.log("Login successful.")
                    return True
                elif 'error' in result:
                    self.status_reason = f"Login Failed: {result['error']}"
                    self.log(self.status_reason, "error")
                    return False
                else:
                    self.status_reason = "Login Failed: Unknown Response"
                    self.log(self.status_reason, "error")
                    return False

            except requests.RequestException as e:
                if attempt == 0:
                    self.log(f"Login network error: {e}. Retrying in 2 seconds...", "error")
                    time.sleep(2)
                else:
                    self.status_reason = f"Login Network Error: {e}"
                    self.log(f"Login failed after retry: {e}", "error")
                    return False
        return False

    def get_credits(self):
        for attempt in range(2):
            try:
                tools_url = f"{self.base_url}/tools"
                response = self.session.get(tools_url, timeout=30)
                soup = BeautifulSoup(response.text, 'html.parser')
                credit_element = soup.find(id="takipKrediCount")
                
                if credit_element:
                    try:
                        val = int(credit_element.text.strip())
                        if val == 0:
                            self.status_reason = "Skipped: 0 Credits"
                        return val
                    except ValueError:
                        self.status_reason = "Skipped: Credit Parse Error"
                        return 0
                else:
                    if attempt == 0:
                        self.log("Credit element not found. Retrying...", "error")
                        time.sleep(2)
                        continue
                    self.status_reason = "Skipped: Credit Element Not Found"
                    return 0

            except requests.RequestException as e:
                if attempt == 0:
                    self.log(f"Get Credits network error: {e}. Retrying in 2 seconds...", "error")
                    time.sleep(2)
                else:
                    self.status_reason = f"Get Credits Error: {e}"
                    self.log(f"Failed to get credits after retry: {e}", "error")
                    return 0
            except Exception as e:
                self.status_reason = f"Get Credits Crash: {e}"
                return 0
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
                self.status_reason = "Failed: Could not extract User ID"
                self.log(self.status_reason, "error")
                return False

            self.log(f"Target ID found: {user_id}. Sending {credit_amount} followers...")
            send_url = f"{response_find.url}?formType=send"
            send_data = {'adet': credit_amount, 'userID': user_id, 'userName': self.target}
            
            response_send = self.session.post(send_url, data=send_data, timeout=30)
            result = response_send.json()

            if result.get('status') == 'success':
                self.log(f"SUCCESS: Sent {credit_amount} followers.")
                self.status_reason = f"Success ({credit_amount} sent)"
                return True
            else:
                self.status_reason = f"API Error: {result.get('message')}"
                self.log(f"FAILED to send: {result.get('message')}", "error")
                return False
        except Exception as e:
            self.status_reason = f"Send Exception: {e}"
            self.log(f"Error sending: {e}", "error")
            return False
            
    def close_session(self):
        try:
            self.session.close()
        except Exception:
            pass

    def run(self):
        if not self.login():
            return False

        credits = self.get_credits()
        self.log(f"Credits available: {credits}")
        
        if credits > 0:
            success = self.send_followers(credits)
            return success
        else:
            self.log("Skipping sending due to 0 credits.")
            # status_reason is already set in get_credits if it was 0 or parse error
            if self.status_reason == "Unknown": 
                self.status_reason = "Skipped: 0 Credits"
            return False

# --- ORCHESTRATION ---

def main():
    print(f"Starting AUTOMATION for target: {TARGET_USER}")
    
    accounts = setup_accounts()
    
    if not accounts:
        print("!! No accounts loaded. Exiting.")
        return

    print(f"Loaded {len(accounts)} accounts.")
    
    # 1. Initialize Report Data
    summary_data = []
    success_count = 0
    fail_count = 0

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
            final_status = "FAILED"
            reason = "Script Crash"
            
            try:
                bot = PanelBot(site_url, current_user, password, TARGET_USER)
                success = bot.run()
                
                # Retrieve the reason from the bot instance
                reason = bot.status_reason
                
                if success:
                    final_status = "SUCCESS"
                    success_count += 1
                    print(f"{site_url} | Operation succeeded.")
                    
                    if POST_TASK_WAIT > 0:
                        print(f">> Waiting {POST_TASK_WAIT}s for completion...")
                        time.sleep(POST_TASK_WAIT)
                else:
                    fail_count += 1
                    print(f"{site_url} | Operation failed or skipped.")
            
            except Exception as e:
                logging.error(f"{site_url} | Unexpected error: {e}")
                reason = str(e)
                fail_count += 1
            
            finally:
                # 2. Add to Summary Data
                summary_data.append({
                    "account": current_user,
                    "site": site_url,
                    "status": final_status,
                    "reason": reason
                })

                if bot:
                    bot.close_session()

            if i < len(WEBSITES) - 1:
                delay = random.uniform(INTER_SITE_DELAY[0], INTER_SITE_DELAY[1])
                print(f">> Cooldown: Waiting {delay:.2f} seconds...")
                time.sleep(delay)

    # 3. Print Final Report
    print("\n\n" + "="*80)
    print(f"FINAL REPORT - TOTAL: {success_count + fail_count} | SUCCESS: {success_count} | FAILED: {fail_count}")
    print("="*80)
    # Header
    print(f"{'ACCOUNT':<15} | {'WEBSITE':<30} | {'STATUS':<10} | REASON")
    print("-" * 80)
    
    for item in summary_data:
        # Simplify URL for cleaner table (remove https://)
        clean_site = item['site'].replace('https://', '').split('/')[0]
        
        print(f"{item['account']:<15} | {clean_site:<30} | {item['status']:<10} | {item['reason']}")
        
    print("="*80)
    print("All tasks completed.")

if __name__ == "__main__":
    main()

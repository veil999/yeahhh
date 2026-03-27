#!/usr/bin/env python3
"""
Pekora Limited Watcher - Cloudflare Bypass Edition
"""

import requests
import time
import json
import os
from datetime import datetime, timezone
import shutil
import threading
from requests_html import HTMLSession  # NEW: For JS/Cloudflare bypass
import random

MIDNIGHT_BLUE = "\033[38;2;50;70;168m"
RESET = "\033[0m"

def print_startup_banner():
    ASCII_BANNER = r"""
       .---.    .-./`) ,---.    ,---. 
       | ,_|    \ .-.')|    \  /    | 
     ,-./  )    / `-' \|  ,  \/  ,  | 
     \  '_ '`)   `-'`"`|  |\_   /|  | 
      > (_)  )   .---. |  _( )_/ |  | 
     (  .  .-'   |   | | (_ o _) |  | 
      `-'`-'|___ |   | |  (_,_)  |  | 
       |        \|   | |  |      |  | 
       `--------`'---' '--'      '--' 
    """
    terminal_width = shutil.get_terminal_size((80, 20)).columns
    for line in ASCII_BANNER.splitlines():
        print(line.center(terminal_width))
    fetching_text = f"{MIDNIGHT_BLUE}[~]{RESET} Fetching... (Cloudflare Bypass Active)"
    print(fetching_text.center(terminal_width))

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_URL_2 = os.getenv("WEBHOOK_URL_2")
CHECK_INTERVAL = 0.5
SEARCH_URL = "https://www.pekora.zip/apisite/catalog/v1/search/items?category=Collectibles&limit=28&sortType=3"
DETAILS_URL = "https://www.pekora.zip/apisite/catalog/v1/catalog/items/details"
SEEN_IDS_FILE = "seen_ids.json"

# UPGRADED HEADERS - Full browser fingerprint
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.pekora.zip/",
    "Origin": "https://www.pekora.zip",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Cookie": os.getenv("COOKIE", ""),  # Keep your cookie
    "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="122", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"'
}

USE_PROXY = False
HTTP_PROXY = "http://TV4GO0:1Z7dhD8iey@188.130.129.54:5500"
PROXIES = {"http": HTTP_PROXY, "https": HTTP_PROXY} if USE_PROXY else None

DEBUG_MODE = True

EMOJIS = {
    "title": "<:Koroneicon:1412988880478539919>",
    "name": "🪦",
    "price": "💰",
    "type": {
        "Limited": "🟢",
        "LimitedUnique": "🟡"
    },
    "id": "💳",
    "link": "<:chainlock:1391363049146945616>"
}

EMBED_COLOR = 0x9295BA
PING_MESSAGE = "@everyone son"

seen_ids = set()

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def debug_print(*args):
    if DEBUG_MODE:
        print(f"[DEBUG {now_str()}]", *args)

def load_seen_ids():
    global seen_ids
    if os.path.isfile(SEEN_IDS_FILE):
        try:
            with open(SEEN_IDS_FILE, "r") as f:
                data = json.load(f)
                seen_ids = set(map(str, data)) if isinstance(data, list) else set()
        except:
            seen_ids = set()

def save_seen_ids():
    try:
        with open(SEEN_IDS_FILE, "w") as f:
            json.dump(list(seen_ids), f)
    except:
        pass

# NEW: Cloudflare/JS bypass function
def cloudflare_bypass_request(session, url, method='GET', **kwargs):
    """Tries regular request first, falls back to HTMLSession with JS rendering"""
    try:
        # Try normal request first (faster)
        resp = session.request(method, url, **kwargs)
        if resp.status_code == 200 and 'json' in resp.headers.get('content-type', '').lower():
            return resp
        elif resp.status_code in [403, 429, 503]:  # Cloudflare blocks
            debug_print(f"Cloudflare detected ({resp.status_code}), trying JS bypass...")
        else:
            debug_print(f"Unexpected status: {resp.status_code}, location: {resp.headers.get('Location')}")
            return resp
    except Exception as e:
        debug_print(f"Regular request failed: {e}")
    
    # Fallback to JS rendering
    try:
        html_session = HTMLSession()
        html_session.headers.update(HEADERS)
        if PROXIES:
            html_session.proxies.update(PROXIES)
        
        resp = html_session.get(url, **kwargs)
        resp.html.render(timeout=20, keep_page=True, scrolldown=1)  # Render JS/Cloudflare challenge
        
        # Extract JSON from rendered page (common CF bypass pattern)
        json_data = None
        for script in resp.html.find('script'):
            if 'window.__cf' in script.text or 'data' in script.text:
                # Try to extract JSON from inline scripts
                pass
        
        # If still no JSON, return rendered HTML for debugging
        if 'json' not in resp.text.lower():
            debug_print("JS render didn't give JSON, saving HTML for debug...")
            with open('debug.html', 'w') as f:
                f.write(resp.html.html)
        
        html_session.close()
        return resp
    except Exception as e:
        debug_print(f"JS bypass failed: {e}")
        return None

def get_limiteds():
    """Enhanced with Cloudflare bypass"""
    session = requests.Session()
    session.headers.update(HEADERS)
    if PROXIES:
        session.proxies.update(PROXIES)
    
    # Pre-flight: Visit homepage to set cookies
    try:
        session.get("https://www.pekora.zip/", timeout=10)
        debug_print("Homepage pre-flight successful")
    except:
        pass
    
    resp = cloudflare_bypass_request(session, SEARCH_URL, timeout=15)
    
    if not resp or resp.status_code != 200:
        debug_print(f"Failed to fetch limiteds: {resp.status_code if resp else 'No response'}")
        return []
    
    try:
        data = resp.json().get("data") or []
        debug_print(f"Fetched {len(data)} items")
        return [data[0]] if data else []
    except:
        debug_print("Failed to parse JSON response")
        if hasattr(resp, 'html'):
            debug_print("Response was HTML, likely Cloudflare challenge")
        return []

def get_item_details(item_id):
    session = requests.Session()
    session.headers.update(HEADERS)
    if PROXIES:
        session.proxies.update(PROXIES)
    
    try:
        payload = {"items": [{"id": int(item_id)}]}
        headers = dict(HEADERS)
        headers["Content-Type"] = "application/json"
        
        resp = cloudflare_bypass_request(session, DETAILS_URL, 'POST', 
                                       json=payload, headers=headers, timeout=15)
        
        if not resp or resp.status_code != 200:
            return None
            
        data = resp.json().get("data") or []
        if not data:
            return None
        d = data[0]

        restrictions_list = d.get("itemRestrictions", [])
        restrictions = ", ".join([EMOJIS["type"].get(r, r) for r in restrictions_list]) if restrictions_list else "None"

        units = d.get("unitsAvailableForConsumption", "N/A")
        return {
            "name": d.get("name", "Unknown"),
            "price": d.get("price", "N/A"),
            "restrictions": restrictions,
            "units": units
        }
    except:
        return None

def send_request(url, payload):
    try:
        requests.post(url, json=payload, timeout=8, proxies=PROXIES)
    except:
        pass

def send_webhook(item_id, name, price, restrictions, units):
    link = f"https://www.pekora.zip/catalog/{item_id}/qqqqqqqq"
    
    fields = [
        {"name": f"{EMOJIS['name']} Name", "value": name, "inline": False},
        {"name": f"{EMOJIS['price']} Price", "value": f"{price} $", "inline": True},
        {"name": f"{EMOJIS['type'].get(restrictions, '🪦')} Type", "value": restrictions, "inline": True},
        {"name": f"{EMOJIS['id']} ID", "value": str(item_id), "inline": False},
        {"name": "📦 Units", "value": str(units), "inline": True},    
        {"name": f"{EMOJIS['link']} Catalog", "value": f"[=================]({link})", "inline": False}
    ]

    payload1 = {
        "content": PING_MESSAGE,
        "embeds": [{
            "title": f"{EMOJIS['title']} x_x",
            "url": link,
            "color": EMBED_COLOR,
            "fields": fields,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    }

    payload2 = {
        "content": PING_MESSAGE,
        "embeds": [{
            "title": f"{EMOJIS['title']} u_u",
            "url": link,
            "color": 0xA2E3C4,
            "fields": fields,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    }

    try:
        threading.Thread(target=send_request, args=(WEBHOOK_URL, payload1)).start()
        if WEBHOOK_URL_2:
            threading.Thread(target=send_request, args=(WEBHOOK_URL_2, payload2)).start()
    except:
        pass

def main_loop():
    load_seen_ids()
    while True:
        try:
            limiteds = get_limiteds()
            if not limiteds:
                time.sleep(CHECK_INTERVAL)
                continue
            item_id = str(limiteds[0].get("id"))
            if not item_id or item_id in seen_ids:
                time.sleep(CHECK_INTERVAL)
                continue
            details = get_item_details(item_id)
            if not details:
                time.sleep(CHECK_INTERVAL)
                continue
            send_webhook(item_id, details["name"], details["price"], details["restrictions"], details["units"])
            seen_ids.add(item_id)
            save_seen_ids()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            debug_print(f"Loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    print_startup_banner()
    while True:
        try:
            main_loop()
        except Exception as e:
            print(f"Fatal error: {e}")
            time.sleep(10)

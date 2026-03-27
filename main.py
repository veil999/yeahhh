#!/usr/bin/env python3
"""
Pekora Limited Watcher - Cloudflare Bypass (Lightweight)
"""

import requests
import cloudscraper  # Cloudflare bypassq
import time
import json
import os
from datetime import datetime, timezone
import shutil
import threading
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
    print(f"{MIDNIGHT_BLUE}[~]{RESET} Fetching... (Cloudscraper Active)".center(terminal_width))

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_URL_2 = os.getenv("WEBHOOK_URL_2")
CHECK_INTERVAL = 0.5
SEARCH_URL = "https://www.pekora.zip/apisite/catalog/v1/search/items?category=Collectibles&limit=28&sortType=3"
DETAILS_URL = "https://www.pekora.zip/apisite/catalog/v1/catalog/items/details"
SEEN_IDS_FILE = "seen_ids.json"

# FULL BROWSER HEADERS
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
    "Cookie": os.getenv("COOKIE", ""),
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

def create_scraper():
    """Create cloudscraper session with proxy support"""
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        },
        delay=10  # Random delay between requests
    )
    scraper.headers.update(HEADERS)
    if PROXIES:
        scraper.proxies.update(PROXIES)
    return scraper

def get_limiteds():
    scraper = create_scraper()
    
    # Pre-flight homepage
    try:
        scraper.get("https://www.pekora.zip/", timeout=15)
        debug_print("Homepage cookies set")
    except Exception as e:
        debug_print(f"Homepage preflight failed: {e}")
    
    try:
        resp = scraper.get(SEARCH_URL, timeout=15)
        debug_print(f"Search status: {resp.status_code}, {len(resp.content)} bytes")
        
        if resp.status_code != 200:
            debug_print(f"Failed: {resp.status_code} - {resp.text[:200]}")
            return []
            
        data = resp.json().get("data") or []
        debug_print(f"Got {len(data)} items")
        return [data[0]] if data else []
        
    except json.JSONDecodeError:
        debug_print("Not JSON response - Cloudflare HTML?")
        with open('debug_response.html', 'w') as f:
            f.write(resp.text)
        debug_print("Saved debug_response.html - check it")
        return []
    except Exception as e:
        debug_print(f"Get limiteds error: {e}")
        return []

def get_item_details(item_id):
    scraper = create_scraper()
    
    try:
        payload = {"items": [{"id": int(item_id)}]}
        headers = dict(HEADERS)
        headers["Content-Type"] = "application/json"
        
        resp = scraper.post(DETAILS_URL, json=payload, headers=headers, timeout=15)
        debug_print(f"Details status: {resp.status_code}")
        
        if resp.status_code != 200:
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

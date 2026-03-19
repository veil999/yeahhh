#!/usr/bin/env python3
"""
Pekora Limited Watcher
Monitors the first item in Pekora's catalog and sends a Discord webhook
when a new limited item appears, with optional debug prints.
"""

import requests
import time
import json
import os
from datetime import datetime, timezone
import shutil

# === ART ===
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
    
    # Get current terminal width
    terminal_width = shutil.get_terminal_size((80, 20)).columns

    # Print each line of the banner centered
    for line in ASCII_BANNER.splitlines():
        print(line.center(terminal_width))

    # Print the fetching line centered
    fetching_text = f"	   	  	{MIDNIGHT_BLUE}[~]{RESET} Fetching..."
    print(fetching_text.center(terminal_width))

# === CONFIG ===
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
CHECK_INTERVAL = 0.5  # seconds
SEARCH_URL = "https://www.pekora.zip/apisite/catalog/v1/search/items?category=Collectibles&limit=28&sortType=3"
DETAILS_URL = "https://www.pekora.zip/apisite/catalog/v1/catalog/items/details"
SEEN_IDS_FILE = "seen_ids.json"

# === HEADERS (Paste your full cookie here) ===
HEADERS = {
    "Cookie": os.getenv("COOKIE"),
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# === PROXY CONFIG ===
USE_PROXY = False  # Toggle proxy usage: True or False

# Format: "http://username:password@ip:port"
HTTP_PROXY = "http://TV4GO0:1Z7dhD8iey@188.130.129.54:5500"

PROXIES = {
    "http": HTTP_PROXY,
} if USE_PROXY else None

# === DEBUG MODE ===
DEBUG_MODE = False  # Set to False to disable debug prints

# === EMOJIS CONFIG ===
EMOJIS = {
    "title": "<:Koroneicon:1412988880478539919>",
    "name": "🪦",
    "price": "💰",
    "type": {  # mapping itemRestrictions
        "Limited": "🟢",
        "LimitedUnique": "🟡"
    },
    "id": "💳",
    "link": "<:chainlock:1391363049146945616>"
}

EMBED_COLOR = 0x3246A8
PING_MESSAGE = "@everyone son"

# === INTERNAL STATE ===
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
            with open(SEEN_IDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    seen_ids = set(map(str, data))
                else:
                    seen_ids = set()
        except Exception as e:
            debug_print("Failed to load seen IDs:", e)
            seen_ids = set()


def save_seen_ids():
    try:
        with open(SEEN_IDS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(seen_ids)), f, indent=2)
    except Exception as e:
        debug_print("Failed to save seen IDs:", e)


def get_limiteds():
    """Fetch the first item from the search endpoint"""
    try:
        resp = requests.get(SEARCH_URL, headers=HEADERS, timeout=8, proxies=PROXIES)
        resp.raise_for_status()
        j = resp.json()
        items = j.get("data") or []
        debug_print("Fetched items:", [i.get("id") for i in items])
        return [items[0]] if items else []
    except Exception as e:
        debug_print("Error fetching limiteds:", e)
        return []


def get_item_details(item_id):
    """Fetch details for a single item ID using correct API payload"""
    try:
        payload = {"items": [{"id": int(item_id)}]}
        headers = dict(HEADERS)
        headers["Content-Type"] = "application/json"
        resp = requests.post(DETAILS_URL, json=payload, headers=headers, timeout=8, proxies=PROXIES)
        resp.raise_for_status()
        j = resp.json()
        data_list = j.get("data") or []
        if not data_list or not isinstance(data_list, list):
            return None
        details = data_list[0] or {}
        name = details.get("name") or "Unknown"
        price = details.get("price") or "N/A"
        restrictions_list = details.get("itemRestrictions") or []
        restrictions = ", ".join([EMOJIS["type"].get(r, r) for r in restrictions_list]) if restrictions_list else "None"
        debug_print(f"Details for {item_id}:", details)
        return {"name": name, "price": price, "restrictions": restrictions}
    except Exception as e:
        debug_print("Error fetching item details:", e)
        return None


def send_webhook(item_id, name, price, restrictions):
    catalog_link = f"https://www.pekora.zip/catalog/{item_id}/LIMITED"
    fields = [
        {"name": f"{EMOJIS['name']} Name", "value": name, "inline": False},
        {"name": f"{EMOJIS['price']} Price", "value": f"{price} $", "inline": True},
        {"name": f"{EMOJIS['type'].get(restrictions, '🪦')} Type", "value": restrictions, "inline": True},
        {"name": f"{EMOJIS['id']} ID", "value": str(item_id), "inline": False},
        {"name": f"{EMOJIS['link']} Catalog", "value": f"[Open in catalog]({catalog_link})", "inline": False}
    ]
    embed = {
        "title": f"{EMOJIS['title']} New Limited Item Found!",
        "url": catalog_link,
        "color": EMBED_COLOR,
        "fields": fields,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": f"Detected at {now_str()}"}
    }
    payload = {"content": PING_MESSAGE, "embeds": [embed]}
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=8, proxies=PROXIES)
        debug_print(f"Webhook sent for ID {item_id}")
    except Exception as e:
        debug_print("Exception sending webhook:", e)


def main_loop():
    load_seen_ids()

    # First run
    limiteds = get_limiteds()
    if limiteds:
        first_item = limiteds[0]
        item_id = str(first_item.get("id"))
        if item_id not in seen_ids:
            details = get_item_details(item_id)
            if details:
                send_webhook(item_id, details["name"], details["price"], details["restrictions"])
                seen_ids.add(item_id)
                save_seen_ids()

    # Main loop
    while True:
        try:
            limiteds = get_limiteds()
            if not limiteds:
                time.sleep(CHECK_INTERVAL)
                continue

            first_item = limiteds[0]
            item_id = str(first_item.get("id"))

            if not item_id or item_id in seen_ids:
                time.sleep(CHECK_INTERVAL)
                continue

            details = get_item_details(item_id)
            if not details:
                time.sleep(CHECK_INTERVAL)
                continue

            send_webhook(item_id, details["name"], details["price"], details["restrictions"])
            seen_ids.add(item_id)
            save_seen_ids()

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)


if __name__ == "__main__":
    if "YOUR_FULL_COOKIE_HERE" in HEADERS.get("Cookie", ""):
        print("⚠️  Please paste your full session cookie into HEADERS['Cookie'].")
    elif "YOUR_WEBHOOK_HERE" in WEBHOOK_URL:
        print("⚠️  Please replace WEBHOOK_URL with your Discord webhook URL.")
    else:
        print_startup_banner()
        while True:
    try:
        main_loop()
    except Exception as e:
        print("Fatal error:", e)
        time.sleep(10)

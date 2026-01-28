import os
import time
import requests
import datetime
import random
import json
import xml.etree.ElementTree as ET
from supabase import create_client, Client

# --- CONFIG ---
SUPABASE_URL = "https://mymlbldoignrhvkfqcnz.supabase.co"
SUPABASE_KEY = "sb_publishable_Yce1uZCUK7isWfD7t8c5iA_Yi9OhtVh"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- SOURCES ---
NEWS_QUERY = "(protest OR riot OR police OR ICE OR whipple OR standoff OR crash OR arrest) AND (site:startribune.com OR site:wcco.com OR site:kstp.com OR site:mprnews.org) when:12h"
NEWS_RSS_URL = f"https://news.google.com/rss/search?q={requests.utils.quote(NEWS_QUERY)}&ceid=US:en&hl=en-US&gl=US"
ARCGIS_URL = "https://www.arcgis.com/sharing/rest/content/items/081587d29d944a89ad189b1633e509e4?f=json"

# WAZE CONFIG (Minneapolis Bounding Box)
WAZE_URL = "https://na-georss.waze.com/rtserver/web/TGeoRSS"
WAZE_PARAMS = {
    "bottom": 44.890, "top": 45.050,  
    "left": -93.350, "right": -93.190, 
    "ma": "600", "mj": "100", "mu": "100", 
    "types": "alerts,traffic"
}
# NEW: Stealth Headers to mimic a real Mac user
WAZE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.waze.com/live-map/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"'
}

LOCATIONS = {
    "whipple": (44.8940, -93.1760), "downtown": (44.9765, -93.2761),
    "uptown": (44.9497, -93.2933), "capitol": (44.9543, -93.1022),
    "minneapolis": (44.9778, -93.2650), "st paul": (44.9537, -93.0900)
}

def get_utc_now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def analyze_intel(text):
    text = text.lower()
    if any(x in text for x in ["sports", "varsity", "hockey", "basketball", "baseball", "recipe", "weather", "forecast", "lottery"]): return None
    if any(x in text for x in ["riot", "protest", "shoot", "fire", "kill", "dead", "standoff", "gun", "attack", "threat"]): return "protest"
    if any(x in text for x in ["police", "cop", "officer", "sheriff", "trooper", "ice", "agent", "arrest", "federal", "court", "judge"]): return "police"
    if any(x in text for x in ["crash", "accident", "closed", "closure", "blocked", "traffic", "detour"]): return "road_closure"
    return "intel"

def single_scan():
    print(">>> SCANNING ALL SOURCES (NEWS + WAZE + DOT)...")
    events = []
    
    # 1. WAZE (Real-Time User Reports)
    try:
        resp = requests.get(WAZE_URL, params=WAZE_PARAMS, headers=WAZE_HEADERS, timeout=10)
        
        # DEBUG CHECK: Did they block us?
        if resp.status_code != 200:
            print(f"!! Waze Blocked Us: Status {resp.status_code}")
        else:
            data = resp.json()
            if 'alerts' in data:
                count = 0
                for alert in data['alerts']:
                    w_type = alert.get('type', '')
                    lat = alert['location']['y']
                    lng = alert['location']['x']
                    desc = alert.get('reportDescription', '')
                    
                    final_type = "road_closure"
                    title = f"WAZE: {w_type}"
                    
                    if w_type == 'POLICE':
                        final_type = "police"
                        title = "WAZE: POLICE REPORTED"
                    elif w_type == 'JAM': continue # Skip simple traffic jams to save clutter
                    elif w_type == 'ACCIDENT':
                        final_type = "road_closure"
                        title = "WAZE: ACCIDENT"
                    
                    events.append({
                        "id": f"waze-{alert.get('uuid', random.randint(1000,9999))}",
                        "title": title, "lat": lat, "lng": lng, "type": final_type,
                        "desc": desc if desc else f"User report near {alert.get('street', 'Minneapolis')}",
                        "timestamp": get_utc_now()
                    })
                    count += 1
                print(f" > Waze Alerts Found: {count}")
                
    except Exception as e: print(f"Waze Err: {e}")

    # 2. NEWS RSS
    try:
        resp = requests.get(NEWS_RSS_URL, timeout=10)
        root = ET.fromstring(resp.content)
        for item in root.findall('.//item'):
            title = item.find('title').text
            etype = analyze_intel(title)
            if not etype: continue
            
            lat, lng = 44.9778, -93.2650
            for k, v in LOCATIONS.items():
                if k in title.lower(): lat, lng = v; break
            
            lat += random.uniform(-0.01, 0.01)
            lng += random.uniform(-0.01, 0.01)
            
            events.append({
                "id": f"news-{hash(title)}", "title": f"INTEL: {title[:60]}...",
                "lat": lat, "lng": lng, "type": etype, "desc": title, "timestamp": get_utc_now()
            })
    except Exception as e: print(f"News Err: {e}")

    # 3. DOT / ARCGIS
    try:
        meta = requests.get(ARCGIS_URL, timeout=10).json()
        if 'url' in meta:
            features = requests.get(f"{meta['url']}/0/query", params={"where":"1=1","outFields":"*","f":"json"}, timeout=15).json().get("features", [])
            for f in features:
                if 'y' in f.get('geometry', {}):
                    attr = f.get('attributes', {})
                    raw_title = attr.get('Headline') or attr.get('EventType')
                    if not raw_title: continue 
                    
                    events.append({
                        "id": f"road-{attr.get('EventID', random.randint(10000,99999))}",
                        "title": f"DOT: {raw_title}",
                        "lat": f['geometry']['y'], "lng": f['geometry']['x'],
                        "type": "road_closure", "desc": attr.get('EventDescription',''),
                        "timestamp": get_utc_now()
                    })
    except Exception as e: print(f"Road Err: {e}")

    # UPLOAD
    if events:
        unique = {e['id']: e for e in events}.values()
        ids = [e['id'] for e in unique]
        try:
            existing = supabase.table('events').select('id, first_seen').in_('id', ids).execute().data
            exist_map = {r['id']: r['first_seen'] for r in existing}
            final = []
            for item in unique:
                if item['id'] in exist_map: item['first_seen'] = exist_map[item['id']]
                else: item['first_seen'] = item['timestamp']
                final.append(item)
            supabase.table('events').upsert(final).execute()
            print(f"Uploaded {len(final)} items (Waze/News/DOT).")
        except Exception as e: print(f"Upload Err: {e}")

if __name__ == "__main__":
    for i in range(4):
        single_scan()
        if i < 3: time.sleep(60)

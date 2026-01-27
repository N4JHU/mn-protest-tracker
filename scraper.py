import os
import time
import requests
import datetime
import random
import xml.etree.ElementTree as ET
from supabase import create_client, Client

# --- CONFIG ---
SUPABASE_URL = "https://mymlbldoignrhvkfqcnz.supabase.co"
SUPABASE_KEY = "sb_publishable_Yce1uZCUK7isWfD7t8c5iA_Yi9OhtVh"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

NEWS_QUERY = "(protest OR riot OR police OR ICE OR whipple OR standoff OR crash OR arrest) AND (site:startribune.com OR site:wcco.com OR site:kstp.com OR site:mprnews.org) when:12h"
NEWS_RSS_URL = f"https://news.google.com/rss/search?q={requests.utils.quote(NEWS_QUERY)}&ceid=US:en&hl=en-US&gl=US"
ARCGIS_URL = "https://www.arcgis.com/sharing/rest/content/items/081587d29d944a89ad189b1633e509e4?f=json"

LOCATIONS = {
    "whipple": (44.8940, -93.1760),
    "downtown": (44.9765, -93.2761),
    "uptown": (44.9497, -93.2933),
    "capitol": (44.9543, -93.1022),
    "minneapolis": (44.9778, -93.2650),
    "st paul": (44.9537, -93.0900)
}

def analyze_intel(text):
    text = text.lower()
    if any(x in text for x in ["sports", "varsity", "hockey", "basketball", "baseball", "recipe", "weather", "forecast", "lottery"]): return None
    if any(x in text for x in ["riot", "protest", "shoot", "fire", "kill", "dead", "standoff", "gun", "attack", "threat"]): return "protest"
    if any(x in text for x in ["police", "cop", "officer", "sheriff", "trooper", "ice", "agent", "arrest", "federal", "court", "judge"]): return "police"
    if any(x in text for x in ["crash", "accident", "closed", "closure", "blocked", "traffic", "detour"]): return "road_closure"
    return "intel"

def get_utc_now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def single_scan():
    print(">>> SCANNING SOURCES...")
    events = []
    
    # NEWS
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

    # TRAFFIC
    try:
        meta = requests.get(ARCGIS_URL, timeout=10).json()
        if 'url' in meta:
            features = requests.get(f"{meta['url']}/0/query", params={"where":"1=1","outFields":"*","f":"json"}, timeout=15).json().get("features", [])
            for f in features:
                if 'y' in f.get('geometry', {}):
                    attr = f.get('attributes', {})
                    events.append({
                        "id": f"road-{attr.get('EventID', random.randint(10000,99999))}",
                        "title": f"TRAFFIC: {attr.get('EventType')}",
                        "lat": f['geometry']['y'], "lng": f['geometry']['x'],
                        "type": "road_closure", "desc": attr.get('EventDescription',''),
                        "timestamp": get_utc_now()
                    })
    except Exception as e: print(f"Road Err: {e}")

   # --- PHASE 3: SMART UPLOAD (PRESERVE HISTORY) ---
    if events:
        # 1. Deduplicate the new batch
        unique_new = {e['id']: e for e in events}.values()
        
        # 2. Get list of IDs we are about to upload
        new_ids = [e['id'] for e in unique_new]
        
        # 3. Ask Database: "Which of these already exist?"
        existing_rows = supabase.table('events').select('id, first_seen').in_('id', new_ids).execute().data
        existing_map = {row['id']: row['first_seen'] for row in existing_rows}
        
        # 4. Merge: Keep old 'first_seen' if exists, otherwise use 'now'
        final_upload = []
        for item in unique_new:
            if item['id'] in existing_map:
                item['first_seen'] = existing_map[item['id']] # KEEP ORIGINAL START TIME
            else:
                item['first_seen'] = item['timestamp'] # NEW EVENT
            final_upload.append(item)

        print(f"Uploading {len(final_upload)} Intelligent Items...")
        try:
            supabase.table('events').upsert(final_upload).execute()
            print("--- UPLOAD SUCCESSFUL ---")
        except Exception as e: print(f"!! Upload Failed: {e}")
    else:
        print("--- NO RELEVANT INTEL FOUND ---")

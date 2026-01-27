import os
import requests
import datetime
import random
import xml.etree.ElementTree as ET
from supabase import create_client, Client

# --- 1. SUPABASE CONFIGURATION ---
SUPABASE_URL = "https://mymlbldoignrhvkfqcnz.supabase.co"
SUPABASE_KEY = "sb_publishable_Yce1uZCUK7isWfD7t8c5iA_Yi9OhtVh"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. INTELLIGENCE SOURCES ---
# Broad search to catch everything, then we filter in Python
NEWS_QUERY = "(protest OR riot OR police OR ICE OR whipple OR standoff OR crash OR arrest) AND (site:startribune.com OR site:wcco.com OR site:kstp.com OR site:mprnews.org) when:12h"
NEWS_RSS_URL = f"https://news.google.com/rss/search?q={requests.utils.quote(NEWS_QUERY)}&ceid=US:en&hl=en-US&gl=US"
ARCGIS_URL = "https://www.arcgis.com/sharing/rest/content/items/081587d29d944a89ad189b1633e509e4?f=json"

# --- 3. THE "BRAIN" (CLASSIFIER) ---
def analyze_intel(text):
    text = text.lower()
    
    # 1. IGNORE (Noise Filter)
    ignore_words = ["sports", "varsity", "hockey", "basketball", "baseball", "recipe", "weather", "forecast", "lottery", "gophers", "vikings", "twins", "wild", "wolves"]
    if any(x in text for x in ignore_words):
        return None # Throw away

    # 2. SEVERE THREAT (RED)
    if any(x in text for x in ["riot", "protest", "shoot", "fire", "kill", "dead", "standoff", "gun", "attack", "threat", "emergency"]):
        return "protest" # Red

    # 3. POLICE / GOV (BLUE)
    if any(x in text for x in ["police", "cop", "officer", "sheriff", "trooper", "ice", "agent", "arrest", "federal", "court", "judge", "jail", "charged"]):
        return "police" # Blue

    # 4. TRAFFIC (ORANGE)
    if any(x in text for x in ["crash", "accident", "closed", "closure", "blocked", "traffic", "detour"]):
        return "road_closure" # Orange

    # 5. GENERAL INTEL (GREY)
    return "intel" # Grey

LOCATIONS = {
    "whipple": (44.8940, -93.1760),
    "downtown": (44.9765, -93.2761),
    "uptown": (44.9497, -93.2933),
    "capitol": (44.9543, -93.1022),
    "minneapolis": (44.9778, -93.2650),
    "st paul": (44.9537, -93.0900)
}

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def get_intel():
    print("--- STARTING INTELLIGENT SCAN ---")
    events = []
    
    # --- PHASE 1: NEWS SCAN ---
    try:
        print("Scanning News Feeds...")
        resp = requests.get(NEWS_RSS_URL, timeout=10)
        root = ET.fromstring(resp.content)
        for item in root.findall('.//item'):
            title = item.find('title').text
            
            # CLASSIFY
            event_type = analyze_intel(title)
            if not event_type:
                continue # Skip Noise
            
            # LOCATE
            lat, lng = 44.9778, -93.2650
            for key, coords in LOCATIONS.items():
                if key in title.lower(): lat, lng = coords; break
            
            # Jitter
            lat += random.uniform(-0.015, 0.015)
            lng += random.uniform(-0.015, 0.015)
            
            events.append({
                "id": f"news-{hash(title)}",
                "title": f"INTEL: {title[:60]}...",
                "lat": lat, "lng": lng, 
                "type": event_type,
                "desc": title, 
                "timestamp": get_utc_now()
            })
    except Exception as e: print(f"!! News Error: {e}")

    # --- PHASE 2: TRAFFIC SCAN ---
    try:
        print("Scanning Road Sensors...")
        meta = requests.get(ARCGIS_URL, timeout=10).json()
        if 'url' in meta:
            query_url = f"{meta['url']}/0/query"
            params = {"where": "1=1", "outFields": "*", "f": "json"}
            features = requests.get(query_url, params=params, timeout=15).json().get("features", [])
            for f in features:
                attr = f.get('attributes', {})
                geom = f.get('geometry', {})
                if 'y' in geom:
                    title = attr.get('Headline') or attr.get('EventType') or "Road Closure"
                    events.append({
                        "id": f"road-{attr.get('EventID', random.randint(10000,99999))}",
                        "title": f"TRAFFIC: {title}",
                        "lat": geom['y'], "lng": geom['x'], 
                        "type": "road_closure",
                        "desc": attr.get('EventDescription', 'Check 511mn.org'),
                        "timestamp": get_utc_now()
                    })
    except Exception as e: print(f"!! Road Error: {e}")

    # --- PHASE 3: DEDUPLICATE & UPLOAD ---
    if events:
        unique_events = {e['id']: e for e in events}.values()
        clean_list = list(unique_events)
        print(f"Uploading {len(clean_list)} Verified Intel Items...")
        try:
            supabase.table('events').upsert(clean_list).execute()
            print("--- UPLOAD SUCCESSFUL ---")
        except Exception as e: print(f"!! Upload Failed: {e}")
    else:
        print("--- NO RELEVANT INTEL FOUND ---")

if __name__ == "__main__":
    get_intel()

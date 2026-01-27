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
NEWS_QUERY = "(protest OR riot OR police OR ICE OR whipple OR standoff OR crash) AND (site:startribune.com OR site:wcco.com OR site:kstp.com OR site:mprnews.org) when:12h"
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

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def get_intel():
    print("--- STARTING TACTICAL SCAN ---")
    events = []
    
    # --- PHASE 1: NEWS SCAN ---
    try:
        print("Scanning News Feeds...")
        resp = requests.get(NEWS_RSS_URL, timeout=10)
        root = ET.fromstring(resp.content)
        for item in root.findall('.//item'):
            title = item.find('title').text
            lat, lng = 44.9778, -93.2650 # Default
            for key, coords in LOCATIONS.items():
                if key in title.lower(): lat, lng = coords; break
            
            # Jitter to prevent stacking
            lat += random.uniform(-0.015, 0.015)
            lng += random.uniform(-0.015, 0.015)
            
            events.append({
                "id": f"news-{hash(title)}",
                "title": f"INTEL: {title[:60]}...",
                "lat": lat, "lng": lng, 
                "type": "protest",
                "desc": title, 
                "timestamp": get_utc_now()
            })
    except Exception as e: print(f"!! News Error: {e}")

    # --- PHASE 2: TRAFFIC SCAN ---
    try:
        print("Scanning DOT Road Sensors...")
        meta = requests.get(ARCGIS_URL, timeout=10).json()
        if 'url' in meta:
            query_url = f"{meta['url']}/0/query"
            params = {"where": "1=1", "outFields": "*", "f": "json"}
            features = requests.get(query_url, params=params, timeout=15).json().get("features", [])
            
            for f in features:
                attr = f.get('attributes', {})
                geom = f.get('geometry', {})
                if 'y' in geom:
                    raw_title = attr.get('Headline') or attr.get('EventType') or "Road Closure"
                    events.append({
                        "id": f"road-{attr.get('EventID', random.randint(10000,99999))}",
                        "title": f"TRAFFIC: {raw_title}",
                        "lat": geom['y'], "lng": geom['x'], 
                        "type": "road_closure",
                        "desc": attr.get('EventDescription', 'Check 511mn.org'),
                        "timestamp": get_utc_now()
                    })
    except Exception as e: print(f"!! Road Error: {e}")

    # --- PHASE 3: DEDUPLICATE & UPLOAD ---
    if events:
        print(f"Raw Intel Count: {len(events)}")
        
        # *** THE FIX: Remove duplicates by ID ***
        # This creates a dictionary where the Key is the ID. 
        # If two items have the same ID, the second one overwrites the first, automatically removing duplicates.
        unique_events = {e['id']: e for e in events}.values()
        clean_list = list(unique_events)
        
        print(f"Clean Intel Count: {len(clean_list)} (Removed {len(events) - len(clean_list)} duplicates)")
        
        try:
            data, count = supabase.table('events').upsert(clean_list).execute()
            print("--- UPLOAD SUCCESSFUL ---")
        except Exception as e: print(f"!! Upload Failed: {e}")
    else:
        print("--- NO NEW INTEL FOUND ---")

if __name__ == "__main__":
    get_intel()

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
# Source A: Google News (Civil Unrest Keywords)
NEWS_QUERY = "(protest OR riot OR police OR ICE OR whipple OR standoff OR crash) AND (site:startribune.com OR site:wcco.com OR site:kstp.com OR site:mprnews.org) when:12h"
NEWS_RSS_URL = f"https://news.google.com/rss/search?q={requests.utils.quote(NEWS_QUERY)}&ceid=US:en&hl=en-US&gl=US"

# Source B: MN Dept of Transportation (Road Closures via ArcGIS)
ARCGIS_URL = "https://www.arcgis.com/sharing/rest/content/items/081587d29d944a89ad189b1633e509e4?f=json"

# Target Zones (For mapping news that doesn't have exact coordinates)
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
        count = 0
        for item in root.findall('.//item'):
            title = item.find('title').text
            
            # Determine Location based on text match
            lat, lng = 44.9778, -93.2650 # Default to City Center
            for key, coords in LOCATIONS.items():
                if key in title.lower(): 
                    lat, lng = coords
                    break
            
            # Add "Jitter" so dots don't stack perfectly on top of each other
            lat += random.uniform(-0.015, 0.015)
            lng += random.uniform(-0.015, 0.015)
            
            events.append({
                "id": f"news-{hash(title)}",
                "title": f"INTEL: {title[:60]}...",
                "lat": lat, "lng": lng, 
                "type": "protest", # Default Red Dot for News
                "desc": title, 
                "timestamp": get_utc_now()
            })
            count += 1
        print(f" > News Items Found: {count}")
    except Exception as e: print(f"!! News Error: {e}")

    # --- PHASE 2: TRAFFIC SCAN ---
    try:
        print("Scanning DOT Road Sensors...")
        # 1. Get the real data URL from the ArcGIS metadata
        meta = requests.get(ARCGIS_URL, timeout=10).json()
        if 'url' in meta:
            query_url = f"{meta['url']}/0/query"
            params = {"where": "1=1", "outFields": "*", "f": "json"}
            
            # 2. Fetch the live incidents
            features = requests.get(query_url, params=params, timeout=15).json().get("features", [])
            
            for f in features:
                attr = f.get('attributes', {})
                geom = f.get('geometry', {})
                
                # Only map if it has coordinates
                if 'y' in geom:
                    # Clean up the title
                    raw_title = attr.get('Headline') or attr.get('EventType') or "Road Closure"
                    
                    events.append({
                        "id": f"road-{attr.get('EventID', random.randint(10000,99999))}",
                        "title": f"TRAFFIC: {raw_title}",
                        "lat": geom['y'], "lng": geom['x'], 
                        "type": "road_closure", # Orange Dot
                        "desc": attr.get('EventDescription', 'Check 511mn.org'),
                        "timestamp": get_utc_now()
                    })
            print(f" > Road Incidents Found: {len(features)}")
    except Exception as e: print(f"!! Road Error: {e}")

    # --- PHASE 3: UPLOAD TO COMMAND CENTER ---
    if events:
        print(f"Uploading {len(events)} total events to Supabase...")
        try:
            # upsert=True prevents duplicates
            data, count = supabase.table('events').upsert(events).execute()
            print("--- UPLOAD SUCCESSFUL ---")
        except Exception as e: print(f"!! Upload Failed: {e}")
    else:
        print("--- NO NEW INTEL FOUND ---")

if __name__ == "__main__":
    get_intel()

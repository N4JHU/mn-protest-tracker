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

# --- SOURCES ---
# 1. GOOGLE NEWS (Filtered for MN Scanner/Incident Keywords)
NEWS_QUERY = "(protest OR riot OR police OR SWAT OR standoff OR crash OR 'road closed') AND (site:startribune.com OR site:wcco.com OR site:kstp.com OR site:mprnews.org OR site:bringmethenews.com) when:12h"
NEWS_RSS_URL = f"https://news.google.com/rss/search?q={requests.utils.quote(NEWS_QUERY)}&ceid=US:en&hl=en-US&gl=US"

# 2. MN DOT 511 (Official Sensors)
ARCGIS_URL = "https://www.arcgis.com/sharing/rest/content/items/081587d29d944a89ad189b1633e509e4?f=json"

LOCATIONS = {
    "whipple": (44.8940, -93.1760), "downtown": (44.9765, -93.2761),
    "uptown": (44.9497, -93.2933), "capitol": (44.9543, -93.1022),
    "minneapolis": (44.9778, -93.2650), "st paul": (44.9537, -93.0900),
    "brooklyn center": (45.0748, -93.3296)
}

def get_utc_now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def analyze_intel(text):
    text = text.lower()
    # FILTER NOISE
    if any(x in text for x in ["sports", "varsity", "hockey", "basketball", "baseball", "recipe", "weather", "forecast", "lottery", "concert"]): return None
    
    # CLASSIFY
    if any(x in text for x in ["riot", "protest", "shoot", "fire", "kill", "dead", "standoff", "gun", "attack", "threat", "swat"]): return "protest"
    if any(x in text for x in ["police", "cop", "officer", "sheriff", "trooper", "ice", "agent", "arrest", "federal", "court", "judge"]): return "police"
    if any(x in text for x in ["crash", "accident", "closed", "closure", "blocked", "traffic", "detour", "stall", "hazard"]): return "road_closure"
    return "intel"

def single_scan():
    print(">>> SCANNING OPEN SOURCES (NEWS + DOT)...")
    events = []
    
    # A. NEWS RSS
    try:
        resp = requests.get(NEWS_RSS_URL, timeout=10)
        root = ET.fromstring(resp.content)
        for item in root.findall('.//item'):
            title = item.find('title').text
            etype = analyze_intel(title)
            if not etype: continue
            
            # Default Location
            lat, lng = 44.9778, -93.2650
            # Try to find specific neighborhood match
            for k, v in LOCATIONS.items():
                if k in title.lower(): lat, lng = v; break
            
            # Add Jitter so dots don't stack
            lat += random.uniform(-0.015, 0.015)
            lng += random.uniform(-0.015, 0.015)
            
            events.append({
                "id": f"news-{hash(title)}", "title": f"INTEL: {title[:60]}...",
                "lat": lat, "lng": lng, "type": etype, "desc": title, "timestamp": get_utc_now()
            })
    except Exception as e: print(f"News Err: {e}")

    # B. MN DOT / ARCGIS
    try:
        meta = requests.get(ARCGIS_URL, timeout=10).json()
        if 'url' in meta:
            # Query the Feature Server
            features = requests.get(f"{meta['url']}/0/query", params={"where":"1=1","outFields":"*","f":"json"}, timeout=15).json().get("features", [])
            for f in features:
                if 'y' in f.get('geometry', {}):
                    attr = f.get('attributes', {})
                    raw_title = attr.get('Headline') or attr.get('EventType')
                    if not raw_title: continue 
                    
                    # Refine Type based on description
                    etype = "road_closure"
                    desc = attr.get('EventDescription','').lower()
                    if "crash" in desc or "accident" in desc: etype = "road_closure" # Orange
                    elif "police" in desc or "law enforcement" in desc: etype = "police" # Blue (Rare in DOT, but possible)
                    
                    events.append({
                        "id": f"road-{attr.get('EventID', random.randint(10000,99999))}",
                        "title": f"DOT: {raw_title}",
                        "lat": f['geometry']['y'], "lng": f['geometry']['x'],
                        "type": etype, 
                        "desc": attr.get('EventDescription',''),
                        "timestamp": get_utc_now()
                    })
    except Exception as e: print(f"Road Err: {e}")

    # UPLOAD & HISTORY PRESERVATION
    if events:
        # 1. Unique by ID
        unique = {e['id']: e for e in events}.values()
        ids = [e['id'] for e in unique]
        
        try:
            # 2. Check which ones are updates vs new
            existing = supabase.table('events').select('id, first_seen').in_('id', ids).execute().data
            exist_map = {r['id']: r['first_seen'] for r in existing}
            
            final = []
            for item in unique:
                if item['id'] in exist_map: 
                    item['first_seen'] = exist_map[item['id']] # Keep original start time
                else: 
                    item['first_seen'] = item['timestamp'] # Set start time to now
                final.append(item)
                
            supabase.table('events').upsert(final).execute()
            print(f"Uploaded {len(final)} Verified Items.")
        except Exception as e: print(f"Upload Err: {e}")

if __name__ == "__main__":
    for i in range(4):
        single_scan()
        if i < 3: time.sleep(60)

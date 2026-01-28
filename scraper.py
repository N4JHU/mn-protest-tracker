import os
import time
import requests
import datetime
import random
import hashlib
import xml.etree.ElementTree as ET
from supabase import create_client, Client

# --- CONFIG ---
SUPABASE_URL = "https://mymlbldoignrhvkfqcnz.supabase.co"
SUPABASE_KEY = "sb_publishable_Yce1uZCUK7isWfD7t8c5iA_Yi9OhtVh"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- SOURCES ---
NEWS_QUERY = "(protest OR riot OR police OR SWAT OR standoff OR crash OR 'road closed') AND (site:startribune.com OR site:wcco.com OR site:kstp.com OR site:mprnews.org OR site:bringmethenews.com) when:12h"
NEWS_RSS_URL = f"https://news.google.com/rss/search?q={requests.utils.quote(NEWS_QUERY)}&ceid=US:en&hl=en-US&gl=US"
ARCGIS_URL = "https://www.arcgis.com/sharing/rest/content/items/081587d29d944a89ad189b1633e509e4?f=json"

LOCATIONS = {
    "whipple": (44.8940, -93.1760), "downtown": (44.9765, -93.2761),
    "uptown": (44.9497, -93.2933), "capitol": (44.9543, -93.1022),
    "minneapolis": (44.9778, -93.2650), "st paul": (44.9537, -93.0900),
    "brooklyn center": (45.0748, -93.3296)
}

def get_utc_now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

# Helper to create stable IDs (No more random duplicates)
def generate_id(prefix, text, lat, lng):
    # Create a unique fingerprint based on title + location
    raw = f"{text}-{lat:.4f}-{lng:.4f}" 
    hash_object = hashlib.md5(raw.encode())
    return f"{prefix}-{hash_object.hexdigest()[:10]}"

def analyze_intel(text):
    text = text.lower()
    if any(x in text for x in ["sports", "varsity", "hockey", "basketball", "baseball", "recipe", "weather", "forecast", "lottery", "concert"]): return None
    if any(x in text for x in ["riot", "protest", "shoot", "fire", "kill", "dead", "standoff", "gun", "attack", "threat", "swat"]): return "protest"
    if any(x in text for x in ["police", "cop", "officer", "sheriff", "trooper", "ice", "agent", "arrest", "federal", "court", "judge"]): return "police"
    if any(x in text for x in ["crash", "accident", "closed", "closure", "blocked", "traffic", "detour", "stall", "hazard"]): return "road_closure"
    return "intel"

def single_scan():
    print(">>> SCANNING SOURCES (SMART DEDUPLICATION)...")
    events = []
    
    # A. NEWS RSS
    try:
        resp = requests.get(NEWS_RSS_URL, timeout=10)
        root = ET.fromstring(resp.content)
        for item in root.findall('.//item'):
            title = item.find('title').text
            etype = analyze_intel(title)
            if not etype: continue
            
            # Default
            lat, lng = 44.9778, -93.2650
            for k, v in LOCATIONS.items():
                if k in title.lower(): lat, lng = v; break
            
            # Only jitter NEWS items (Traffic is precise)
            final_lat = lat + random.uniform(-0.015, 0.015)
            final_lng = lng + random.uniform(-0.015, 0.015)
            
            # Use original lat/lng for ID generation so jitter doesn't break deduplication
            events.append({
                "id": generate_id("news", title, lat, lng), 
                "title": f"INTEL: {title[:60]}...",
                "lat": final_lat, "lng": final_lng, 
                "type": etype, "desc": title, "timestamp": get_utc_now()
            })
    except Exception as e: print(f"News Err: {e}")

    # B. MN DOT
    try:
        meta = requests.get(ARCGIS_URL, timeout=10).json()
        if 'url' in meta:
            features = requests.get(f"{meta['url']}/0/query", params={"where":"1=1","outFields":"*","f":"json"}, timeout=15).json().get("features", [])
            for f in features:
                if 'y' in f.get('geometry', {}):
                    attr = f.get('attributes', {})
                    raw_title = attr.get('Headline') or attr.get('EventType')
                    if not raw_title: continue 
                    
                    etype = "road_closure"
                    desc = attr.get('EventDescription','').lower()
                    if "police" in desc or "law enforcement" in desc: etype = "police"
                    
                    lat = f['geometry']['y']
                    lng = f['geometry']['x']

                    # Use Official EventID if available, otherwise generate stable Hash
                    if attr.get('EventID'):
                        eid = f"road-{attr.get('EventID')}"
                    else:
                        eid = generate_id("road", raw_title, lat, lng)

                    events.append({
                        "id": eid,
                        "title": f"DOT: {raw_title}",
                        "lat": lat, "lng": lng,
                        "type": etype, 
                        "desc": attr.get('EventDescription',''),
                        "timestamp": get_utc_now()
                    })
    except Exception as e: print(f"Road Err: {e}")

    # UPLOAD
    if events:
        unique = {e['id']: e for e in events}.values() # Deduplicate by ID immediately
        final = list(unique)
        
        # Preserve History Logic
        ids = [e['id'] for e in final]
        try:
            existing = supabase.table('events').select('id, first_seen').in_('id', ids).execute().data
            exist_map = {r['id']: r['first_seen'] for r in existing}
            for item in final:
                if item['id'] in exist_map: item['first_seen'] = exist_map[item['id']]
                else: item['first_seen'] = item['timestamp']
            
            supabase.table('events').upsert(final).execute()
            print(f"Uploaded {len(final)} Verified Items.")
        except Exception as e: print(f"Upload Err: {e}")

if __name__ == "__main__":
    for i in range(4):
        single_scan()
        if i < 3: time.sleep(60)

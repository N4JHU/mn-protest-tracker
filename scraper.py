import json
import datetime
import os
import requests
import time
import urllib3
import random
import xml.etree.ElementTree as ET
import re

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
OUTPUT_FILE = "events.json"
DB_RETENTION_DAYS = 15

# ROAD SOURCE: ArcGIS Feature Service (Proven Working)
ARCGIS_METADATA_URL = "https://www.arcgis.com/sharing/rest/content/items/081587d29d944a89ad189b1633e509e4?f=json"

# PROTEST SOURCES
# 1. Google News RSS (Targeted Search)
NEWS_RSS_URL = "https://news.google.com/rss/search?q=protest+minneapolis+when:48h&ceid=US:en&hl=en-US&gl=US"
# 2. Reddit Communities to Scan
REDDIT_SUBS = ["Minneapolis", "TwinCities", "Minnesota"]

# KEYWORDS (What triggers a Red Dot?)
THREAT_KEYWORDS = ["protest", "march", "riot", "blocking traffic", "shutdown", "demonstration", "sit-in", "standoff"]

# LANDMARK MAPPING (Simple Text-to-Geo)
# If the text mentions "Uptown", we map it to 44.94, -93.29
LOCATIONS = {
    "capitol": (44.9543, -93.1022),
    "uptown": (44.9497, -93.2933),
    "downtown": (44.9765, -93.2761),
    "city hall": (44.9761, -93.2636),
    "3rd precinct": (44.9481, -93.2356),
    "94": (44.9650, -93.2750), # Generic I-94 Spot
    "35w": (44.9740, -93.2540), # Generic 35W Spot
    "hennepin": (44.9800, -93.2600),
}

# --- 1. ROAD SCRAPER (Keep Existing) ---
def get_live_road_closures():
    print("--- Connecting to ArcGIS Feature Server ---")
    events = []
    try:
        meta_response = requests.get(ARCGIS_METADATA_URL, timeout=15)
        service_url = meta_response.json().get("url")
        if not service_url: return []

        query_url = f"{service_url}/0/query"
        params = {"where": "1=1", "outFields": "*", "f": "json"}
        
        response = requests.get(query_url, params=params, timeout=30)
        features = response.json().get("features", [])
        
        for feature in features:
            attrs = feature.get("attributes", {})
            geom = feature.get("geometry", {})
            lat, lng = geom.get("y"), geom.get("x")
            
            if lat and lng:
                title = attrs.get("Headline") or attrs.get("EventType") or "Road Event"
                if title and "test" not in title.lower():
                    events.append({
                        "id": attrs.get("EventID") or f"arc-{attrs.get('OBJECTID')}",
                        "title": title,
                        "lat": float(lat),
                        "lng": float(lng),
                        "type": "road_closure",
                        "desc": attrs.get("EventDescription", "See 511mn.org"),
                        "timestamp": datetime.datetime.now().isoformat()
                    })
        print(f"--- SUCCESS: Found {len(events)} road events.")
        return events
    except Exception as e:
        print(f"!! Road Scraper Error: {e}")
        return []

# --- 2. PROTEST SCRAPER (New!) ---
def get_social_threats():
    print("--- Scanning Social Media & News ---")
    events = []
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

    # A. GOOGLE NEWS SCAN
    try:
        print(f"Scanning Google News RSS...")
        resp = requests.get(NEWS_RSS_URL, headers=headers, timeout=10)
        root = ET.fromstring(resp.content)
        
        for item in root.findall('.//item'):
            title = item.find('title').text
            link = item.find('link').text
            pubDate = item.find('pubDate').text
            
            # Check Keywords
            if any(k in title.lower() for k in THREAT_KEYWORDS):
                # Geolocate
                lat, lng = (44.9778, -93.2650) # Default: Mpls City Center
                detected_loc = "General Alert"
                
                for landmark, coords in LOCATIONS.items():
                    if landmark in title.lower():
                        lat, lng = coords
                        detected_loc = landmark.title()
                        # Add tiny random jitter so dots don't stack
                        lat += random.uniform(-0.002, 0.002)
                        lng += random.uniform(-0.002, 0.002)
                        break

                events.append({
                    "id": f"news-{hash(title)}",
                    "title": f"REPORT: {title[:50]}...",
                    "lat": lat,
                    "lng": lng,
                    "type": "protest",
                    "desc": f"Source: Google News ({detected_loc})\nLink: {link}",
                    "timestamp": datetime.datetime.now().isoformat()
                })
    except Exception as e:
        print(f"!! News Error: {e}")

    # B. REDDIT SCAN
    try:
        for sub in REDDIT_SUBS:
            print(f"Scanning r/{sub}...")
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=25"
            # Reddit REQUIRES a unique User-Agent or it blocks you
            resp = requests.get(url, headers={"User-Agent": "MN-Tracker-Bot/1.0"}, timeout=10)
            
            if resp.status_code == 200:
                posts = resp.json().get("data", {}).get("children", [])
                for post in posts:
                    data = post.get("data", {})
                    title = data.get("title", "")
                    
                    if any(k in title.lower() for k in THREAT_KEYWORDS):
                        # Geolocate
                        lat, lng = (44.9778, -93.2650)
                        detected_loc = "Unverified"
                        
                        for landmark, coords in LOCATIONS.items():
                            if landmark in title.lower():
                                lat, lng = coords
                                detected_loc = landmark.title()
                                lat += random.uniform(-0.002, 0.002)
                                lng += random.uniform(-0.002, 0.002)
                                break
                        
                        events.append({
                            "id": f"reddit-{data.get('id')}",
                            "title": f"REDDIT: {title[:40]}...",
                            "lat": lat,
                            "lng": lng,
                            "type": "protest",
                            "desc": f"User: u/{data.get('author')}\nLoc: {detected_loc}\n{data.get('url')}",
                            "timestamp": datetime.datetime.now().isoformat()
                        })
            time.sleep(1) # Be polite to Reddit
    except Exception as e:
        print(f"!! Reddit Error: {e}")

    print(f"--- SUCCESS: Found {len(events)} potential threats.")
    return events

# --- MAIN ENGINE ---
def main():
    print("--- STARTING UPDATE JOB ---")
    
    # 1. Load History
    existing_events = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r") as f:
                data = json.load(f)
                existing_events = data.get("features", [])
        except: existing_events = []
    
    # 2. Fetch New Data
    new_events = []
    new_events.extend(get_live_road_closures())
    new_events.extend(get_social_threats()) # <--- NEW FUNCTION ADDED HERE

    # 3. Merge & Save
    event_db = {e["id"]: e for e in existing_events} 
    for event in new_events:
        event_db[event["id"]] = event
    
    # Filter Old Data
    cutoff = datetime.datetime.now() - datetime.timedelta(days=DB_RETENTION_DAYS)
    final_features = [e for e in event_db.values() if e.get("timestamp") and datetime.datetime.fromisoformat(e["timestamp"]) > cutoff]

    with open(OUTPUT_FILE, "w") as f:
        json.dump({"last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "features": final_features}, f, indent=2)
    
    print(f"--- DATABASE UPDATED: {len(final_features)} Total Events ---")

if __name__ == "__main__":
    main()
    

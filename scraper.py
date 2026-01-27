import json
import datetime
import os
import requests
import time
import urllib3
import random
import xml.etree.ElementTree as ET

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
OUTPUT_FILE = "events.json"
DB_RETENTION_DAYS = 15

# --- 1. ROAD DATA SOURCE (MnDOT/ArcGIS) ---
ARCGIS_METADATA_URL = "https://www.arcgis.com/sharing/rest/content/items/081587d29d944a89ad189b1633e509e4?f=json"

# --- 2. INTELLIGENCE SOURCES ---
# Targeted Google News Command
NEWS_QUERY = (
    "(protest OR riot OR march OR police OR crash OR gunfire OR standoff) "
    "AND ("
    "site:startribune.com OR site:wcco.com OR site:kstp.com OR "
    "site:kare11.com OR site:mprnews.org OR site:bringmethenews.com OR "
    "site:dps.mn.gov OR site:minneapolismn.gov OR site:stpaul.gov OR "
    "site:aclu-mn.org OR site:cuapb.org"
    ") when:12h"
)
NEWS_RSS_URL = f"https://news.google.com/rss/search?q={requests.utils.quote(NEWS_QUERY)}&ceid=US:en&hl=en-US&gl=US"

REDDIT_SUBS = ["Minneapolis", "TwinCities", "Minnesota", "AltMpls"]
THREAT_KEYWORDS = ["riot", "tear gas", "standoff", "looting", "shots fired", "shuts down", "blocking"]
VIGIL_KEYWORDS = ["vigil", "gathering", "march", "rally", "memorial", "protest"]

LOCATIONS = {
    "capitol": (44.9543, -93.1022),
    "gov": (44.9543, -93.1022),
    "uptown": (44.9497, -93.2933),
    "downtown": (44.9765, -93.2761),
    "city hall": (44.9761, -93.2636),
    "3rd precinct": (44.9481, -93.2356),
    "1st precinct": (44.9775, -93.2650),
    "hennepin": (44.9780, -93.2630),
    "94": (44.9650, -93.2750),
    "35w": (44.9740, -93.2540),
    "fort snelling": (44.8940, -93.1760),
    "whipple": (44.8940, -93.1760),
    "airport": (44.8848, -93.2223),
}

# --- HELPER: UTC TIMESTAMP ---
def get_utc_now():
    # Returns 2026-01-26T12:00:00+00:00 (Explicit UTC)
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

# --- MODULE 1: ROAD SCRAPER ---
def get_live_road_closures():
    print("--- Connecting to ArcGIS Feature Server ---")
    events = []
    try:
        meta = requests.get(ARCGIS_METADATA_URL, timeout=10).json()
        service_url = meta.get("url")
        if not service_url: return []

        query_url = f"{service_url}/0/query"
        params = {"where": "1=1", "outFields": "*", "f": "json"}
        resp = requests.get(query_url, params=params, timeout=30)
        features = resp.json().get("features", [])
        
        for feature in features:
            attrs = feature.get("attributes", {})
            geom = feature.get("geometry", {})
            lat, lng = geom.get("y"), geom.get("x")
            
            if lat and lng:
                raw_title = attrs.get("Headline") or attrs.get("EventType") or "Road Event"
                title = "TRAFFIC: " + raw_title
                
                if "test" not in title.lower():
                    events.append({
                        "id": f"road-{attrs.get('EventID', random.randint(1000,9999))}",
                        "title": title,
                        "lat": float(lat),
                        "lng": float(lng),
                        "type": "road_closure",
                        "desc": attrs.get("EventDescription", "See 511mn.org"),
                        "timestamp": get_utc_now()
                    })
        print(f"--- SUCCESS: Found {len(events)} road events.")
        return events
    except Exception as e:
        print(f"!! Road Scraper Error: {e}")
        return []

# --- MODULE 2: INTEL AGGREGATOR ---
def get_intel_feed():
    print("--- Scanning Targeted Intelligence Sources ---")
    events = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    # A. NEWS & OFFICIAL SOURCES
    try:
        print(f"Scanning News/Gov Feed...")
        resp = requests.get(NEWS_RSS_URL, headers=headers, timeout=15)
        root = ET.fromstring(resp.content)
        
        for item in root.findall('.//item'):
            title = item.find('title').text
            link = item.find('link').text
            source_tag = "Unknown"
            if "Star Tribune" in title: source_tag = "Star Tribune"
            elif "WCCO" in title: source_tag = "WCCO (CBS)"
            elif "KSTP" in title: source_tag = "KSTP (ABC)"
            elif "KARE" in title: source_tag = "KARE 11"
            elif "MPR" in title: source_tag = "MPR News"
            elif ".gov" in link: source_tag = "OFFICIAL GOV ALERT"
            
            lat, lng = (44.9778, -93.2650)
            for landmark, coords in LOCATIONS.items():
                if landmark in title.lower():
                    lat, lng = coords
                    break
            
            lat += random.uniform(-0.02, 0.02)
            lng += random.uniform(-0.02, 0.02)

            events.append({
                "id": f"news-{hash(title)}",
                "title": f"INTEL: {title[:60]}...",
                "lat": lat,
                "lng": lng,
                "type": "protest",
                "desc": f"<b>SOURCE: {source_tag}</b><br>{title}<br><br><a href='{link}' target='_blank' style='color:#ff5555'>OPEN SOURCE LINK</a>",
                "timestamp": get_utc_now()
            })
    except Exception as e:
        print(f"!! News Feed Error: {e}")

    # B. REDDIT SCANNER
    try:
        for sub in REDDIT_SUBS:
            print(f"Scanning r/{sub}...")
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=15"
            resp = requests.get(url, headers={"User-Agent": "MN-Intel-Bot/2.0"}, timeout=10)
            
            if resp.status_code == 200:
                posts = resp.json().get("data", {}).get("children", [])
                for post in posts:
                    data = post.get("data", {})
                    title = data.get("title", "")
                    
                    is_threat = any(k in title.lower() for k in THREAT_KEYWORDS)
                    is_vigil = any(k in title.lower() for k in VIGIL_KEYWORDS)
                    
                    if is_threat or is_vigil:
                        lat, lng = (44.9778, -93.2650)
                        for landmark, coords in LOCATIONS.items():
                            if landmark in title.lower():
                                lat, lng = coords
                                break
                        lat += random.uniform(-0.02, 0.02)
                        lng += random.uniform(-0.02, 0.02)
                        tag = "HIGH THREAT" if is_threat else "COMMUNITY"
                        
                        events.append({
                            "id": f"reddit-{data.get('id')}",
                            "title": f"REDDIT: {title[:50]}...",
                            "lat": lat,
                            "lng": lng,
                            "type": "protest",
                            "desc": f"<b>TAG: {tag}</b><br>u/{data.get('author')}: {title}<br><br><a href='https://reddit.com{data.get('permalink')}' target='_blank' style='color:#ff5555'>VIEW THREAD</a>",
                            "timestamp": get_utc_now()
                        })
            time.sleep(1)
    except Exception as e:
        print(f"!! Reddit Error: {e}")

    print(f"--- SUCCESS: Found {len(events)} intel items.")
    return events

# --- MAIN ENGINE ---
def main():
    print("--- STARTING METRO SURGE UPDATE ---")
    
    # Load History
    existing_events = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r") as f:
                data = json.load(f)
                existing_events = data.get("features", [])
        except: existing_events = []
    
    # Fetch New
    new_events = []
    new_events.extend(get_live_road_closures())
    new_events.extend(get_intel_feed())

    # Merge
    event_db = {e["id"]: e for e in existing_events} 
    for event in new_events:
        event_db[event["id"]] = event
    
    # Clean Old Data (Using Offset-Aware Comparison)
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DB_RETENTION_DAYS)
    
    final_features = []
    for e in event_db.values():
        if e.get("timestamp"):
            try:
                # Parse timestamp and ensure it has timezone info
                t_obj = datetime.datetime.fromisoformat(e["timestamp"])
                if t_obj.tzinfo is None:
                    # If old data has no timezone, assume UTC
                    t_obj = t_obj.replace(tzinfo=datetime.timezone.utc)
                
                if t_obj > cutoff:
                    final_features.append(e)
            except:
                continue

    # Save
    with open(OUTPUT_FILE, "w") as f:
        json.dump({
            "last_updated": get_utc_now(), # Global sync timestamp
            "features": final_features
        }, f, indent=2)
    
    print(f"--- DATABASE UPDATED: {len(final_features)} Total Events ---")

if __name__ == "__main__":
    main()

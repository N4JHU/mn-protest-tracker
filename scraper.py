import json
import datetime
import os
import requests
import time
import random
import urllib3
import xml.etree.ElementTree as ET

# Disable SSL warnings (We must skip verification to fix the "Hostname Mismatch" error)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
OUTPUT_FILE = "events.json"
DB_RETENTION_DAYS = 15

# --- SOURCES ---
# Source A: The Official XML Feed (Often more reliable for bots)
XML_URL = "https://lb.511mn.org/mnlb/events/all?format=xml"

# Source B: The Web API (Used by the 511mn.org website itself)
WEB_API_URL = "https://511mn.org/api/events"

def get_live_road_closures():
    print("--- Connecting to MnDOT 511 ---")
    events = []
    
    # 1. Setup a "Session" to look like a real browser
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://511mn.org/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
    })

    # --- ATTEMPT 1: XML FEED ---
    try:
        print(f"Attempting Source A (XML)...")
        # verify=False fixes the SSL Error you saw earlier
        response = session.get(XML_URL, timeout=15, verify=False)
        
        if response.status_code == 200 and "<events" in response.text:
            # Parse XML
            root = ET.fromstring(response.text)
            count = 0
            for event_elem in root.findall('event'):
                try:
                    e_id = event_elem.find('id').text
                    headline = event_elem.find('headline').text or "Traffic Incident"
                    desc = event_elem.find('description').text or ""
                    
                    # Find Lat/Lng (MnDOT XML structure varies, checking common tags)
                    lat, lng = None, None
                    loc = event_elem.find('location')
                    if loc is not None:
                        lat = float(loc.find('lat').text)
                        lng = float(loc.find('lon').text)
                    
                    if lat and lng:
                        events.append({
                            "id": e_id,
                            "title": headline,
                            "lat": lat,
                            "lng": lng,
                            "type": "road_closure",
                            "desc": desc,
                            "timestamp": datetime.datetime.now().isoformat()
                        })
                        count += 1
                except:
                    continue
            
            print(f"--- SUCCESS: Source A (XML) returned {count} events.")
            return events
        else:
            print(f"Source A failed. Status: {response.status_code}")

    except Exception as e:
        print(f"Source A Error: {e}")

    # --- ATTEMPT 2: WEB API (JSON) ---
    try:
        print(f"Switching to Source B (Web API)...")
        # This requires the Referer header we set above
        response = session.get(WEB_API_URL, timeout=15, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            # The Web API returns a specific dictionary structure
            # We look for the main list, usually under specific keys or just the root list
            items = data if isinstance(data, list) else data.get('events', [])
            
            for item in items:
                try:
                    # Filter for real events
                    if "incident" in item.get('type', '').lower() or "closure" in item.get('headline', '').lower():
                         # Extract Location
                        locs = item.get('locations', [{}])
                        if locs:
                            lat = locs[0].get('lat') or locs[0].get('latitude')
                            lng = locs[0].get('lon') or locs[0].get('longitude')
                            
                            if lat and lng:
                                events.append({
                                    "id": item.get('id'),
                                    "title": item.get('headline', 'Road Event'),
                                    "lat": float(lat),
                                    "lng": float(lng),
                                    "type": "road_closure",
                                    "desc": item.get('description', 'Check 511mn.org'),
                                    "timestamp": datetime.datetime.now().isoformat()
                                })
                except:
                    continue
            
            print(f"--- SUCCESS: Source B (Web API) returned {len(events)} events.")
            return events

    except Exception as e:
        print(f"Source B Error: {e}")

    # --- FALLBACK ---
    if not events:
        print("!! ALL SOURCES FAILED. Using 'System Offline' marker.")
        return [{
            "id": "ERR-1", "title": "SYSTEM OFFLINE", 
            "lat": 44.97, "lng": -93.26, "type": "road_closure", 
            "desc": "Could not contact MnDOT servers.", 
            "timestamp": datetime.datetime.now().isoformat()
        }]
    
    return events

# --- PROTEST PLACEHOLDER ---
def get_protests():
    now = datetime.datetime.now()
    return [
        {"id": "MANUAL-1", "title": "Capitol Monitor", "lat": 44.95, "lng": -93.10, "type": "protest", "desc": "Area of interest.", "timestamp": now.isoformat()}
    ]

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
        except:
            existing_events = []
    
    # 2. Fetch New Data
    new_events = []
    new_events.extend(get_live_road_closures())
    new_events.extend(get_protests())

    # 3. Merge
    event_db = {e["id"]: e for e in existing_events} 
    for event in new_events:
        event_db[event["id"]] = event
    
    # 4. Clean (15 Days)
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=DB_RETENTION_DAYS)
    final_features = []
    for event in event_db.values():
        try:
            if event.get("timestamp"):
                if datetime.datetime.fromisoformat(event["timestamp"]) > cutoff_time:
                    final_features.append(event)
            else:
                final_features.append(event)
        except:
            continue

    # 5. Save
    output_data = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "features": final_features
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"--- DATABASE UPDATED: {len(final_features)} Total Events ---")

if __name__ == "__main__":
    main()

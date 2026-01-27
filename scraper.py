import json
import datetime
import os
import requests
import time
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
OUTPUT_FILE = "events.json"
DB_RETENTION_DAYS = 15

# TARGET: MnDOT "Open511" Developer API
# This is the official feed for app developers, distinct from the consumer website.
OPEN511_URL = "https://api.511mn.org/api/events?format=json"

def get_live_road_closures():
    print(f"Connecting to MnDOT Open511 Dev API ({OPEN511_URL})...")
    events = []
    
    # Simple headers - Open511 usually doesn't require complex browser mimicking
    headers = {
        "User-Agent": "MN-Protest-Tracker-Bot/1.0",
        "Accept": "application/json"
    }

    try:
        response = requests.get(OPEN511_URL, headers=headers, timeout=30, verify=False)
        
        # Check if we got a valid JSON response
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"!! Failed to decode JSON. Response text: {response.text[:100]}...")
            return []

        # The API usually returns a simple list of events or a dict with an "events" key
        items = data if isinstance(data, list) else data.get("events", [])
        
        print(f"API returned {len(items)} raw items.")

        for item in items:
            try:
                # Filter for Incidents & Closures
                # Open511 structure: "Type" is often "incident" or "construction"
                event_type = item.get("type", "").lower()
                headline = item.get("headline", "").lower()
                desc = item.get("description", "").lower()

                # KEYWORD FILTER
                is_relevant = False
                if "crash" in headline or "incident" in event_type or "closure" in headline or "blocked" in desc:
                    is_relevant = True
                
                if is_relevant:
                    # LOCATION EXTRACTION
                    # Open511 typically uses "geography" or "locations"
                    lat, lng = None, None
                    
                    # Style 1: "locations" array
                    if "locations" in item and len(item["locations"]) > 0:
                        loc = item["locations"][0]
                        # Sometimes keys are "lat"/"lon", sometimes "latitude"/"longitude"
                        lat = loc.get("lat") or loc.get("latitude")
                        lng = loc.get("lon") or loc.get("longitude")
                    
                    # Style 2: "geography" object (GeoJSON style)
                    elif "geography" in item:
                        coords = item["geography"].get("coordinates", [])
                        if coords:
                            lng, lat = coords # GeoJSON is [Lng, Lat]

                    if lat and lng:
                        events.append({
                            "id": item.get("id"),
                            "title": item.get("headline", "Road Event"),
                            "lat": float(lat),
                            "lng": float(lng),
                            "type": "road_closure",
                            "desc": item.get("description", "See 511mn.org for details"),
                            "timestamp": datetime.datetime.now().isoformat()
                        })
            except Exception as e:
                # Skip bad items silently
                continue

        print(f"--- SUCCESS: Found {len(events)} relevant events.")
        return events

    except Exception as e:
        print(f"!! Critical Error connecting to Open511: {e}")
        return []

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
    road_data = get_live_road_closures()
    
    if road_data:
        new_events.extend(road_data)
    else:
        print("Warning: No road data fetched. Using System Offline marker.")
        # If it fails, add the "Offline" marker so you see it on the map immediately
        new_events.append({
             "id": "ERR-OFFLINE", "title": "SYSTEM OFFLINE", "lat": 44.97, "lng": -93.26, 
             "type": "road_closure", "desc": "Connection to MnDOT failed.", 
             "timestamp": datetime.datetime.now().isoformat()
        })
        
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

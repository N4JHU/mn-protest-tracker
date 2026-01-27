import json
import datetime
import os
import requests
import time
import urllib3

# Disable SSL warnings for the backup feeds if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
OUTPUT_FILE = "events.json"
DB_RETENTION_DAYS = 15

# TARGET: MnDOT Open Data (via ArcGIS Public Feed)
# This is a public geojson feed that doesn't block bots.
DATA_URL = "https://public-iowadot.opendata.arcgis.com/datasets/081587d29d944a89ad189b1633e509e4_0.geojson"

# MINNESOTA BOUNDARIES (Rough Box)
# We use this to filter out Iowa/Wisconsin points that might be in the feed
MN_LAT_MIN, MN_LAT_MAX = 43.4, 49.4
MN_LNG_MIN, MN_LNG_MAX = -97.3, -89.4

def get_live_road_closures():
    print(f"Connecting to Open Data Feed ({DATA_URL})...")
    events = []

    try:
        # 1. Fetch Data
        response = requests.get(DATA_URL, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            features = data.get("features", [])
            print(f"Feed returned {len(features)} total raw items.")
            
            for feature in features:
                try:
                    props = feature.get("properties", {})
                    geom = feature.get("geometry", {})
                    
                    # 2. Extract Coordinates (GeoJSON is [Longitude, Latitude])
                    if geom and geom.get("type") == "Point":
                        lng, lat = geom.get("coordinates")
                        
                        # 3. Filter: Is this point actually in Minnesota?
                        if (MN_LAT_MIN <= lat <= MN_LAT_MAX) and (MN_LNG_MIN <= lng <= MN_LNG_MAX):
                            
                            # Clean up the Title
                            raw_title = props.get("Headline", "Road Event")
                            # Shorten generic titles
                            if "minnesota department of transportation" in raw_title.lower():
                                title = "Roadwork / Alert"
                            else:
                                title = raw_title

                            events.append({
                                "id": props.get("EventID", f"arc-{random.randint(1000,9999)}"),
                                "title": title,
                                "lat": lat,
                                "lng": lng,
                                "type": "road_closure",
                                "desc": props.get("EventDescription", "See local signs."),
                                "timestamp": datetime.datetime.now().isoformat()
                            })
                except Exception:
                    continue

            print(f"--- SUCCESS: Found {len(events)} valid MN events inside state borders.")
            
            # Debug: Print the first one to prove it works
            if len(events) > 0:
                print(f"DEBUG SAMPLE: {events[0]['title']} at {events[0]['lat']}, {events[0]['lng']}")
                
            return events
        
        else:
            print(f"!! Feed Failed. Status Code: {response.status_code}")
            return []

    except Exception as e:
        print(f"!! Critical Error: {e}")
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
    import random # Late import for the ID generation
    
    road_data = get_live_road_closures()
    if road_data:
        new_events.extend(road_data)
    else:
        print("Warning: No road data fetched. Using previous data if available.")
        
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

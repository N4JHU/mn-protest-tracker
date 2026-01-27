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

# TARGET: Iowa/MN DOT ArcGIS "Feature Service"
# We use the Item ID to find the live server URL dynamically.
ARCGIS_ITEM_ID = "081587d29d944a89ad189b1633e509e4"
ARCGIS_METADATA_URL = f"https://www.arcgis.com/sharing/rest/content/items/{ARCGIS_ITEM_ID}?f=json"

def get_live_road_closures():
    print("--- Connecting to ArcGIS Feature Server ---")
    events = []
    
    try:
        # STEP 1: Get the live Server URL from the Metadata
        # This prevents us from guessing the wrong URL or using a dead link.
        meta_response = requests.get(ARCGIS_METADATA_URL, timeout=15)
        meta_data = meta_response.json()
        
        service_url = meta_data.get("url")
        if not service_url:
            print("!! Could not find Service URL in metadata.")
            return []
            
        print(f"Found Live Server: {service_url}")
        
        # STEP 2: Query the Live Server directly
        # We ask for "where=1=1" (Give me everything) in JSON format.
        query_url = f"{service_url}/0/query"
        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "json"
        }
        
        response = requests.get(query_url, params=params, timeout=30)
        data = response.json()
        
        features = data.get("features", [])
        print(f"Server returned {len(features)} live events.")
        
        for feature in features:
            try:
                attrs = feature.get("attributes", {})
                geom = feature.get("geometry", {})
                
                # Extract Location (ArcGIS JSON uses x/y)
                lat = geom.get("y")
                lng = geom.get("x")
                
                # Filter: Ensure it has coordinates
                if lat and lng:
                    # Clean up the Title
                    # "Headline" is usually the best field in this dataset
                    title = attrs.get("Headline") or attrs.get("EventType") or "Road Event"
                    
                    # Filter out test/empty data
                    if title and "test" not in title.lower():
                        events.append({
                            "id": attrs.get("EventID") or f"arc-{attrs.get('OBJECTID')}",
                            "title": title,
                            "lat": float(lat),
                            "lng": float(lng),
                            "type": "road_closure",
                            "desc": attrs.get("EventDescription", "See 511mn.org for details"),
                            "timestamp": datetime.datetime.now().isoformat()
                        })
            except Exception:
                continue

        print(f"--- SUCCESS: Processed {len(events)} valid events.")
        return events

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
    road_data = get_live_road_closures()
    
    if road_data:
        new_events.extend(road_data)
    else:
        print("Warning: No road data fetched. Using System Offline marker.")
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

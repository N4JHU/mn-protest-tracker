import json
import datetime
import os
import requests
import time

# --- CONFIGURATION ---
OUTPUT_FILE = "events.json"
DB_RETENTION_DAYS = 15

# Source A: Official MnDOT Load Balancer (Fastest, but sometimes blocks bots)
SOURCE_A_URL = "https://lb.511mn.org/mnlb/events/all?format=json"

# Source B: Public ArcGIS Feed (Slower, but very reliable/open)
SOURCE_B_URL = "https://public-iowadot.opendata.arcgis.com/datasets/081587d29d944a89ad189b1633e509e4_0.geojson"

# --- REAL DATA FETCHER ---
def get_live_road_closures():
    print(f"Attempting to fetch live road data...")
    events = []

    # --- ATTEMPT 1: MnDOT Direct ---
    try:
        print(f"Trying Source A ({SOURCE_A_URL})...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://511mn.org/"
        }
        response = requests.get(SOURCE_A_URL, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for item in data:
                try:
                    # Filter for only real incidents/closures
                    desc = item.get("description", "").lower()
                    headline = item.get("headline", "").lower()
                    if "closure" in headline or "crash" in headline or "incident" in headline or "blocked" in desc:
                        loc = item.get("locations", [{}])[0]
                        if loc.get("lat") and loc.get("lon"):
                            events.append({
                                "id": item.get("id"),
                                "title": item.get("headline", "Traffic Incident"),
                                "lat": loc.get("lat"),
                                "lng": loc.get("lon"),
                                "type": "road_closure",
                                "desc": item.get("description", "Check local traffic reports."),
                                "timestamp": datetime.datetime.now().isoformat()
                            })
                except:
                    continue
            print(f"--- SUCCESS: Source A provided {len(events)} events.")
            return events
        else:
            print(f"!! Source A Failed with Status Code: {response.status_code}")

    except Exception as e:
        print(f"!! Source A Error: {e}")

    # --- ATTEMPT 2: ArcGIS Backup ---
    print(f"Switching to Backup Source B ({SOURCE_B_URL})...")
    try:
        response = requests.get(SOURCE_B_URL, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for feature in data.get("features", []):
                try:
                    props = feature.get("properties", {})
                    geom = feature.get("geometry", {})
                    
                    # ArcGIS puts coordinates in [long, lat] order
                    if geom.get("type") == "Point":
                        lng, lat = geom.get("coordinates")
                        
                        events.append({
                            "id": props.get("EventID", f"arcgis-{props.get('OBJECTID')}"),
                            "title": props.get("Headline", "Road Event"),
                            "lat": lat,
                            "lng": lng,
                            "type": "road_closure",
                            "desc": props.get("EventDescription", "No details."),
                            "timestamp": datetime.datetime.now().isoformat()
                        })
                except:
                    continue
            print(f"--- SUCCESS: Source B provided {len(events)} events.")
            return events
    except Exception as e:
        print(f"!! Source B Error: {e}")

    # --- FALLBACK: Mock Data (Only if BOTH fail) ---
    print("!! ALL SOURCES FAILED. Reverting to Mock Data.")
    return [
        {"id": "RC-MOCK-1", "title": "DATA LINK SEVERED", "lat": 44.97, "lng": -93.26, "type": "road_closure", "desc": "Could not reach MnDOT servers.", "timestamp": datetime.datetime.now().isoformat()}
    ]

# --- PROTEST PLACEHOLDER ---
def get_protests():
    # Keeping the manual entry so the 'Threats' counter isn't empty
    now = datetime.datetime.now()
    return [
        {"id": "MANUAL-1", "title": "Monitoring: Capitol Area", "lat": 44.95, "lng": -93.10, "type": "protest", "desc": "Manual entry: Area of interest.", "timestamp": now.isoformat()}
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

    # 3. Merge & Clean
    event_db = {e["id"]: e for e in existing_events} 
    for event in new_events:
        event_db[event["id"]] = event
    
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

    # 4. Save
    output_data = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "features": final_features
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"--- DATABASE UPDATED: {len(final_features)} Total Events ---")

if __name__ == "__main__":
    main()

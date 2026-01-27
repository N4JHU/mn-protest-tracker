import json
import datetime
import os

# CONFIGURATION
OUTPUT_FILE = "events.json"
DB_RETENTION_DAYS = 15  # Keep 15 days of history in the file

# --- MOCK DATA GENERATORS ---
def get_road_closures():
    now = datetime.datetime.now()
    return [
        {
            "id": "RC-1", 
            "title": "I-94 East Closure", 
            "lat": 44.96, "lng": -93.27, 
            "type": "road_closure", 
            "desc": "Closed due to maintenance",
            "timestamp": (now - datetime.timedelta(hours=2)).isoformat() # 2 hours ago
        },
        {
            "id": "RC-OLD", 
            "title": "Old Resolved Closure", 
            "lat": 44.93, "lng": -93.22, 
            "type": "road_closure", 
            "desc": "Cleared",
            "timestamp": (now - datetime.timedelta(days=3)).isoformat() # 3 days ago (Should be in DB, but HIDDEN on map)
        },
        {
            "id": "RC-FUTURE", 
            "title": "Scheduled: Parade Route", 
            "lat": 44.98, "lng": -93.26, 
            "type": "road_closure", 
            "desc": "Road will be closed for parade",
            "timestamp": (now + datetime.timedelta(days=1)).isoformat() # Tomorrow
        }
    ]

def get_protests():
    now = datetime.datetime.now()
    return [
        {
            "id": "P-LIVE", 
            "title": "Live: Capitol Gathering", 
            "lat": 44.95, "lng": -93.10, 
            "type": "protest", 
            "desc": "Crowd gathering on steps", 
            "timestamp": now.isoformat() # Now
        },
        {
            "id": "P-WEEK-OLD", 
            "title": "Rally Last Week", 
            "lat": 44.92, "lng": -93.30, 
            "type": "history", 
            "desc": "Historical record", 
            "timestamp": (now - datetime.timedelta(days=7)).isoformat() # 7 days ago (In DB, Hidden on map)
        }
    ]

# --- MAIN LOGIC ---
def main():
    print("--- STARTING UPDATE JOB ---")
    
    # 1. Load Existing Database
    existing_events = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r") as f:
                data = json.load(f)
                existing_events = data.get("features", [])
        except Exception:
            existing_events = []
    
    # 2. Fetch New Data
    new_events = []
    new_events.extend(get_road_closures())
    new_events.extend(get_protests())

    # 3. Merge (New updates overwrite old ones based on ID)
    event_db = {e["id"]: e for e in existing_events} 
    for event in new_events:
        event_db[event["id"]] = event
    
    # 4. Filter: Keep everything from the last 15 DAYS
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=DB_RETENTION_DAYS)
    final_features = []

    for event in event_db.values():
        try:
            event_time = datetime.datetime.fromisoformat(event["timestamp"])
            if event_time > cutoff_time:
                final_features.append(event)
        except (ValueError, KeyError):
            continue # Skip bad data

    # 5. Save to File
    output_data = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "features": final_features
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"--- SUCCESS: Saved {len(final_features)} events (15-day history) to {OUTPUT_FILE} ---")

if __name__ == "__main__":
    main()

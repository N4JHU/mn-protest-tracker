import json
import datetime
import os
import requests
import time

# --- CONFIGURATION ---
OUTPUT_FILE = "events.json"
DB_RETENTION_DAYS = 15
MNDOT_API_URL = "https://lb.511mn.org/mnlb/events/all?format=json"

# --- REAL DATA FETCHER: MnDOT 511 ---
def get_live_road_closures():
    print(f"Connecting to MnDOT Command Center...")
    
    # Header allows us to look like a normal web browser so we don't get blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # 1. Fetch Data
        response = requests.get(MNDOT_API_URL, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        events = []
        
        # 2. Filter & Format Data
        for item in data:
            try:
                # We only want real closures/incidents, not just "future roadwork"
                desc = item.get("description", "").lower()
                headline = item.get("headline", "").lower()
                
                # Keywords that indicate a relevant map event
                if "closure" in headline or "crash" in headline or "incident" in headline or "blocked" in desc:
                    
                    loc = item.get("locations", [{}])[0]
                    
                    if loc.get("lat") and loc.get("lon"):
                        event = {
                            "id": item.get("id"),
                            "title": item.get("headline", "Traffic Incident"),
                            "lat": loc.get("lat"),
                            "lng": loc.get("lon"),
                            "type": "road_closure",
                            "desc": item.get("description", "Check local traffic reports."),
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        events.append(event)
            except Exception:
                continue # Skip messy data

        print(f"--- SUCCESS: Retrieved {len(events)} active events from MnDOT.")
        return events

    except Exception as e:
        print(f"!! CONNECTION FAILED: {e}")
        return []

# --- PLACEHOLDER: PROTEST DATA ---
# (We will build the Social Media Scraper next)
def get_protests():
    # Keeping the manual entry for now so the map isn't empty of red dots
    now = datetime.datetime.now()
    return [
        {
            "id": "MANUAL-1", 
            "title": "Monitoring: Capitol Area", 
            "lat": 44.95, "lng": -93.10, 
            "type": "protest", 
            "desc": "Manual entry: Area of interest.", 
            "timestamp": now.isoformat()
        }
    ]

# --- MAIN ENGINE ---
def main():
    print("--- STARTING UPDATE JOB ---")
    
    # 1. Load History (to keep past events)
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

    # 3. Merge (New data updates old data)
    event_db = {e["id"]: e for e in existing_events} 
    for event in new_events:
        event_db[event["id"]] = event
    
    # 4. Clean Up (Remove events older than 15 days)
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=DB_RETENTION_DAYS)
    final_features = []
    for event in event_db.values():
        try:
            if event.get("timestamp"):
                event_time = datetime.datetime.fromisoformat(event["timestamp"])
                if event_time > cutoff_time:
                    final_features.append(event)
            else:
                final_features.append(event)
        except:
            final_features.append(event)

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

import json
import datetime
import os
import requests
import time
import random

# --- CONFIGURATION ---
OUTPUT_FILE = "events.json"
DB_RETENTION_DAYS = 15

# TARGET: Official MnDOT 511 Feed
MNDOT_API_URL = "https://lb.511mn.org/mnlb/events/all?format=json"

# --- REAL DATA FETCHER ---
def get_live_road_closures():
    print(f"Connecting to MnDOT Command Center...")
    
    # ROTATING HEADERS: Makes the robot look like a real human user
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://511mn.org/",
        "Origin": "https://511mn.org"
    }
    
    events = []

    try:
        # Add a tiny delay to seem more human
        time.sleep(1)
        
        response = requests.get(MNDOT_API_URL, headers=headers, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            for item in data:
                try:
                    # Filter: Only show active issues
                    desc = item.get("description", "").lower()
                    headline = item.get("headline", "").lower()
                    
                    # KEYWORDS: What are we looking for?
                    is_incident = "crash" in headline or "incident" in headline or "stalled" in headline
                    is_closure = "closed" in headline or "closure" in headline or "blocked" in desc
                    
                    if is_incident or is_closure:
                        loc = item.get("locations", [{}])[0]
                        if loc.get("lat") and loc.get("lon"):
                            
                            # Clean up the title
                            title = item.get("headline", "Traffic Incident")
                            if "minnesota department of transportation" in title.lower():
                                title = "Roadwork/Maintenance"

                            events.append({
                                "id": item.get("id"),
                                "title": title,
                                "lat": loc.get("lat"),
                                "lng": loc.get("lon"),
                                "type": "road_closure",
                                "desc": item.get("description", "Check local traffic reports."),
                                "timestamp": datetime.datetime.now().isoformat()
                            })
                except:
                    continue
            
            print(f"--- SUCCESS: MnDOT Link Established. Found {len(events)} events.")
            return events
        
        else:
            print(f"!! MnDOT Blocked Us. Status Code: {response.status_code}")
            return []

    except Exception as e:
        print(f"!! Connection Error: {e}")
        return []

# --- PROTEST PLACEHOLDER (Manual Entry) ---
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
    # Note: If MnDOT fails, we return an empty list rather than fake Iowa data
    mn_data = get_live_road_closures()
    if mn_data:
        new_events.extend(mn_data)
    else:
        print("Warning: No road data fetched this run.")
        
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

import json
import random
import datetime

# OUTPUT FILE
OUTPUT_FILE = "events.json"

# MOCK DATA GENERATORS (Replace these with real API calls later)
def get_road_closures():
    # Simulating fetching from MnDOT 511
    roads = [
        {"id": "RC-1", "title": "I-94 East Closure", "lat": 44.96, "lng": -93.27, "type": "road_closure", "desc": "Closed due to maintenance"},
        {"id": "RC-2", "title": "Hennepin Ave Blocked", "lat": 44.98, "lng": -93.26, "type": "road_closure", "desc": "Police activity reported"}
    ]
    return roads

def get_protests():
    # Simulating fetching from News/Social Media
    protests = [
        {"id": "P-1", "title": "Peaceful March", "lat": 44.95, "lng": -93.10, "type": "protest", "desc": "March headed towards Capitol", "time": "Live Now"},
        {"id": "P-2", "title": "Past: City Hall Rally", "lat": 44.97, "lng": -93.26, "type": "history", "desc": "Occurred 2 days ago", "time": "2023-10-25"}
    ]
    return protests

def main():
    print("Fetching data...")
    
    # 1. Aggregate Data
    all_events = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "features": []
    }
    
    all_events["features"].extend(get_road_closures())
    all_events["features"].extend(get_protests())

    # 2. Save to JSON
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_events, f, indent=2)
    
    print(f"Successfully updated {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

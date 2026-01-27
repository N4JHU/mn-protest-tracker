import os
import random
import datetime
from supabase import create_client, Client

# --- CONFIG ---
SUPABASE_URL = "https://mymlbldoignrhvkfqcnz.supabase.co"
SUPABASE_KEY = "sb_publishable_Yce1uZCUK7isWfD7t8c5iA_Yi9OhtVh"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- GENERATE SIMULATED INTEL ---
def generate_test_data():
    print("--- INITIATING SYSTEM TEST ---")
    events = []
    
    # 1. Simulate Road Closures (Orange)
    print("Generating Simulated Traffic Data...")
    for i in range(5):
        lat = 44.9778 + random.uniform(-0.05, 0.05)
        lng = -93.2650 + random.uniform(-0.05, 0.05)
        events.append({
            "id": f"sim-road-{random.randint(1000,9999)}",
            "title": "TEST: ROAD BLOCKED",
            "lat": lat, "lng": lng, 
            "type": "road_closure",
            "desc": "Simulated blockage for system test.",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

    # 2. Simulate Threats (Red)
    print("Generating Simulated Threat Data...")
    for i in range(3):
        lat = 44.95 + random.uniform(-0.03, 0.03)
        lng = -93.25 + random.uniform(-0.03, 0.03)
        events.append({
            "id": f"sim-threat-{random.randint(1000,9999)}",
            "title": "TEST: GATHERING",
            "lat": lat, "lng": lng, 
            "type": "protest",
            "desc": "Simulated crowd activity.",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

    # 3. Upload
    print(f"Uploading {len(events)} Simulated Events...")
    try:
        data, count = supabase.table('events').upsert(events).execute()
        print("--- UPLOAD SUCCESSFUL ---")
        print("Check your map. You should see 8 new dots immediately.")
    except Exception as e:
        print(f"!!! UPLOAD FAILED: {e}")

if __name__ == "__main__":
    generate_test_data()

import os
import requests
import datetime
import random
import xml.etree.ElementTree as ET
from supabase import create_client, Client

# --- 1. SUPABASE CONFIGURATION ---
# I have inserted your keys here for immediate use.
SUPABASE_URL = "https://mymlbldoignrhvkfqcnz.supabase.co"
SUPABASE_KEY = "sb_publishable_Yce1uZCUK7isWfD7t8c5iA_Yi9OhtVh"

# Initialize the client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. CONFIGURATION & SOURCES ---
# Google News RSS Command (The "Robot Eyes")
NEWS_QUERY = (
    "(protest OR riot OR police OR ICE OR whipple OR standoff OR crash) "
    "AND (site:startribune.com OR site:wcco.com OR site:kstp.com OR site:mprnews.org) when:12h"
)
NEWS_RSS_URL = f"https://news.google.com/rss/search?q={requests.utils.quote(NEWS_QUERY)}&ceid=US:en&hl=en-US&gl=US"

# Target Locations for "Jitter" (Spreading dots out)
LOCATIONS = {
    "whipple": (44.8940, -93.1760),
    "downtown": (44.9765, -93.2761),
    "uptown": (44.9497, -93.2933),
    "capitol": (44.9543, -93.1022)
}

# --- 3. THE SCANNER ---
def get_intel():
    print("--- Scanning Intelligence Feed ---")
    events = []
    
    # A. Scan Google News
    try:
        print(f"Fetching RSS Feed...")
        resp = requests.get(NEWS_RSS_URL, timeout=10)
        # Parse XML
        root = ET.fromstring(resp.content)
        
        for item in root.findall('.//item'):
            title = item.find('title').text
            
            # 1. Default Location (Minneapolis Center)
            lat = 44.9778
            lng = -93.2650
            
            # 2. Check for Specific Landmarks in Title
            title_lower = title.lower()
            for key, coords in LOCATIONS.items():
                if key in title_lower:
                    lat, lng = coords
                    break
            
            # 3. Apply "Jitter" (Random offset so dots don't stack perfectly)
            lat += random.uniform(-0.02, 0.02)
            lng += random.uniform(-0.02, 0.02)
            
            # 4. Create Event Object
            events.append({
                "id": f"news-{hash(title)}",
                "title": f"INTEL: {title[:60]}...",
                "lat": lat,
                "lng": lng,
                "type": "protest", # Defaulting to red 'protest' marker
                "desc": title,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            
    except Exception as e:
        print(f"!! RSS Error: {e}")

    # B. Upload to Supabase
    if events:
        print(f"Found {len(events)} new intel items. Uploading to Database...")
        
        # 'upsert' means "Insert if new, Update if exists" (Prevents duplicates)
        try:
            data, count = supabase.table('events').upsert(events).execute()
            print("--- SUCCESS: Database Updated ---")
        except Exception as e:
            print(f"!! Database Upload Error: {e}")
    else:
        print("--- No new intel found this cycle ---")

# --- EXECUTION ---
if __name__ == "__main__":
    get_intel()

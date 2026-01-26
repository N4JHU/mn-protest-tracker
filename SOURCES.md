# Minnesota Protest Tracker - Data Sources

**Last Updated:** January 26, 2026

## 🎯 Current Status: MANUAL CURATION

The tracker currently uses **manually curated data** stored in `events.json`. The system checks for updates every 60 seconds and will automatically display new data when the JSON file is updated.

## 📊 Data Sources Being Monitored (Manual)

### Government & Official Sources
- **Minnesota Department of Public Safety** - Official incident reports
- **St. Paul Police Department** - Public safety announcements
- **Minneapolis Police Department** - Activity logs
- **Minnesota State Patrol** - Traffic/road closure alerts
- **Hennepin County Sheriff** - Emergency notifications
- **Ramsey County Sheriff** - Public safety updates

### News & Media Sources
- **Star Tribune** - Local breaking news
- **WCCO (CBS Minnesota)** - Live news updates
- **KSTP (ABC 5)** - Traffic and breaking news
- **KARE 11 (NBC)** - Local coverage
- **MPR News (Minnesota Public Radio)** - In-depth reporting
- **Bring Me The News** - Local news aggregator

### Social Media & Community
- **Twitter/X** - Real-time incident reports
  - @MinneapolisPD
  - @StPaulPD
  - @MnDPS_DPS
  - #MNProtest hashtag monitoring
- **Citizen App** - Crowd-sourced incident reports
- **Waze** - Real-time traffic/road closures
- **MnDOT 511** - Official road condition reports

### Community Organizations
- **Communities United Against Police Brutality**
- **Minnesota Freedom Fund**
- **ACLU Minnesota** - Civil rights monitoring
- **Local activist groups** - Planned event announcements

## 🔄 Update Frequency

- **Map Auto-Refresh:** Every 60 seconds
- **Data Review:** Continuous manual monitoring
- **Intel Feed Updates:** Real-time as information becomes available

## 🚀 Future: Automated Data Integration

To enable true real-time monitoring, the following integrations are planned:

### Phase 1: API Integrations
- [ ] MnDOT 511 Traffic API
- [ ] Police scanner feeds (OpenMHz, Broadcastify)
- [ ] Twitter API for hashtag/account monitoring
- [ ] Weather alerts (NWS API)

### Phase 2: Advanced Sources
- [ ] Citizen App API (if available)
- [ ] Waze traffic API
- [ ] News RSS feed aggregation
- [ ] Police radio transcription (Whisper AI)

### Phase 3: AI/ML Enhancement
- [ ] Natural language processing for social media
- [ ] Automatic event classification
- [ ] Severity/risk assessment
- [ ] Predictive crowd movement analysis

## 📝 Data Schema

See `events.json` for the current data structure:
- Event location (lat/lng)
- Event type (protest, road closure, gathering)
- Status badges (ACTIVE CONFLICT, MEMORIAL VIGIL, etc.)
- Timestamps and descriptions
- Intel feed updates

## ⚠️ Disclaimer

This tracker aggregates publicly available information for situational awareness. Data accuracy depends on source reliability. Always verify critical information through official channels.

---

**Maintained by:** N4JHU  
**Project:** https://github.com/N4JHU/mn-protest-tracker  
**Live Map:** https://n4jhu.github.io/mn-protest-tracker/

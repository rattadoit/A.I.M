import os
from datetime import datetime, timedelta
from typing import List

from integrations.base import LocalEvent
from integrations.event_normalizer import haversine_km

try:
    import httpx
except ImportError:
    httpx = None


def load_ticketmaster(
    lat: float,
    lon: float,
    radius_km: float,
    target_date: str,
    day_window: int = 1,
) -> List[LocalEvent]:
    api_key = os.getenv("TICKETMASTER_API_KEY")
    if not api_key or not httpx:
        return []

    center = datetime.strptime(target_date, "%Y-%m-%d")
    start = (center - timedelta(days=day_window)).strftime("%Y-%m-%dT00:00:00Z")
    end = (center + timedelta(days=day_window + 1)).strftime("%Y-%m-%dT23:59:59Z")
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": api_key,
        "latlong": f"{lat},{lon}",
        "radius": int(radius_km),
        "unit": "km",
        "startDateTime": start,
        "endDateTime": end,
        "size": 50,
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []

    events = []
    for item in data.get("_embedded", {}).get("events", []):
        venues = item.get("_embedded", {}).get("venues", [{}])
        venue = venues[0] if venues else {}
        loc = venue.get("location", {})
        vlat = float(loc.get("latitude", lat))
        vlon = float(loc.get("longitude", lon))
        classifications = item.get("classifications", [{}])
        seg = (classifications[0].get("segment", {}) or {}).get("name", "Misc")
        event_type = "concert" if "music" in seg.lower() else "festival"
        events.append(
            LocalEvent(
                canonical_event_id="",
                source="ticketmaster",
                source_event_id=item.get("id", ""),
                name=item.get("name", ""),
                start_at=item.get("dates", {}).get("start", {}).get("dateTime", start),
                end_at=None,
                venue_name=venue.get("name", ""),
                lat=vlat,
                lon=vlon,
                distance_km=haversine_km(lat, lon, vlat, vlon),
                event_type=event_type,
                event_impact_score=0.6,
                affected_categories=[],
                affected_product_ids=[],
            )
        )
    return events

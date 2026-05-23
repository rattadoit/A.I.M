import os
from datetime import datetime, timedelta
from typing import List

from integrations.base import LocalEvent
from integrations.event_normalizer import haversine_km

try:
    import httpx
except ImportError:
    httpx = None


def load_eventbrite(
    lat: float,
    lon: float,
    radius_km: float,
    target_date: str,
    day_window: int = 1,
) -> List[LocalEvent]:
    token = os.getenv("EVENTBRITE_PRIVATE_TOKEN")
    if not token or not httpx:
        return []

    center = datetime.strptime(target_date, "%Y-%m-%d")
    start = (center - timedelta(days=day_window)).isoformat() + "Z"
    end = (center + timedelta(days=day_window + 1)).isoformat() + "Z"
    url = "https://www.eventbriteapi.com/v3/events/search/"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "location.latitude": lat,
        "location.longitude": lon,
        "location.within": f"{radius_km}km",
        "start_date.range_start": start,
        "start_date.range_end": end,
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []

    events = []
    for item in data.get("events", []):
        v = item.get("venue", {}) or {}
        vlat = float(v.get("latitude", lat) or lat)
        vlon = float(v.get("longitude", lon) or lon)
        events.append(
            LocalEvent(
                canonical_event_id="",
                source="eventbrite",
                source_event_id=str(item.get("id", "")),
                name=item.get("name", {}).get("text", ""),
                start_at=item.get("start", {}).get("utc", start),
                end_at=item.get("end", {}).get("utc"),
                venue_name=v.get("name", ""),
                lat=vlat,
                lon=vlon,
                distance_km=haversine_km(lat, lon, vlat, vlon),
                event_type="networking",
                event_impact_score=0.55,
                affected_categories=[],
                affected_product_ids=[],
            )
        )
    return events

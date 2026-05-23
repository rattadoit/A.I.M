import os
from datetime import datetime, timedelta
from typing import List

import pandas as pd

from integrations.base import LocalEvent
from integrations.event_normalizer import haversine_km, filter_events_by_date


def load_ode(
    lat: float,
    lon: float,
    radius_km: float,
    target_date: str,
    day_window: int = 1,
) -> List[LocalEvent]:
    path = os.getenv("ODE_EVENTS_CSV_PATH", "data/ode_events.csv")
    if not os.path.exists(path):
        return []

    try:
        df = pd.read_csv(path)
    except Exception:
        return []

    events = []
    for _, row in df.iterrows():
        elat = float(row.get("lat", lat))
        elon = float(row.get("lon", lon))
        dist = haversine_km(lat, lon, elat, elon)
        if dist > radius_km:
            continue
        events.append(
            LocalEvent(
                canonical_event_id=str(row.get("event_id", "")),
                source="ode",
                source_event_id=str(row.get("event_id", "")),
                name=str(row.get("name", "")),
                start_at=str(row.get("start_at", "")),
                end_at=str(row.get("end_at", "")) if pd.notna(row.get("end_at")) else None,
                venue_name=str(row.get("venue_name", "")),
                lat=elat,
                lon=elon,
                distance_km=dist,
                event_type=str(row.get("event_type", "festival")),
                event_impact_score=float(row.get("event_impact_score", 0.5)),
                affected_categories=[],
                affected_product_ids=[],
            )
        )
    return filter_events_by_date(events, target_date, day_window)

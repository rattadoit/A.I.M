import hashlib
import math
from datetime import datetime, timedelta
from typing import List, Optional

from config import TRADE_AREA_RADIUS_KM
from integrations.base import LocalEvent

EVENT_TYPE_CATEGORY_MAP = {
    "concert": (["주류", "간식"], ["P08", "P09", "P10"]),
    "sports": (["음료", "간식"], ["P04", "P05", "P10"]),
    "festival": (["음료", "주류"], ["P04", "P05", "P08"]),
    "marathon": (["음료"], ["P04", "P02"]),
    "networking": (["음료", "주류", "식사"], ["P02", "P04", "P08", "P06"]),
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def apply_category_mapping(event: LocalEvent) -> LocalEvent:
    if event.affected_categories and event.affected_product_ids:
        return event
    cats, pids = EVENT_TYPE_CATEGORY_MAP.get(
        event.event_type.lower(),
        (["음료", "간식"], ["P04", "P10"]),
    )
    event.affected_categories = event.affected_categories or list(cats)
    event.affected_product_ids = event.affected_product_ids or list(pids)
    return event


def score_event_impact(event: LocalEvent, trade_area: str) -> float:
    base = event.event_impact_score or 0.5
    radius = TRADE_AREA_RADIUS_KM.get(trade_area, 3.0)
    dist_factor = max(0.2, 1.0 - (event.distance_km / max(radius, 0.1)))
    type_boost = {"concert": 1.0, "festival": 0.9, "sports": 0.85}.get(event.event_type.lower(), 0.75)
    return min(1.0, round(base * dist_factor * type_boost, 3))


def _canonical_id(name: str, start_at: str, lat: float, lon: float) -> str:
    key = f"{name.strip().lower()}|{start_at[:10]}|{round(lat, 2)}|{round(lon, 2)}"
    return "evt-" + hashlib.md5(key.encode()).hexdigest()[:10]


def dedupe_events(events: List[LocalEvent], time_thresh_min: int = 120, dist_thresh_km: float = 0.5) -> List[LocalEvent]:
    if not events:
        return []
    sorted_ev = sorted(events, key=lambda e: e.event_impact_score, reverse=True)
    kept: List[LocalEvent] = []
    for ev in sorted_ev:
        dup = False
        try:
            t0 = datetime.fromisoformat(ev.start_at.replace("Z", ""))
        except ValueError:
            t0 = None
        for k in kept:
            try:
                t1 = datetime.fromisoformat(k.start_at.replace("Z", ""))
            except ValueError:
                t1 = None
            if t0 and t1 and abs((t0 - t1).total_seconds()) < time_thresh_min * 60:
                if haversine_km(ev.lat, ev.lon, k.lat, k.lon) < dist_thresh_km:
                    dup = True
                    break
            if ev.name.strip().lower() == k.name.strip().lower():
                dup = True
                break
        if not dup:
            ev.canonical_event_id = ev.canonical_event_id or _canonical_id(ev.name, ev.start_at, ev.lat, ev.lon)
            kept.append(apply_category_mapping(ev))
    return kept


def filter_events_by_date(
    events: List[LocalEvent],
    target_date: str,
    day_window: int = 1,
) -> List[LocalEvent]:
    try:
        center = datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        return events
    start = center - timedelta(days=day_window)
    end = center + timedelta(days=day_window + 1)
    out = []
    for ev in events:
        try:
            t = datetime.fromisoformat(ev.start_at.replace("Z", "").split("+")[0])
        except ValueError:
            out.append(ev)
            continue
        if start <= t < end:
            out.append(ev)
    return out

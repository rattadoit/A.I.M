import json
import os
from typing import List

from integrations.base import SocialTrendSignal, LocalEvent

TRENDS_PATH = "data/sample_trends.json"
EVENTS_PATH = "data/sample_events.json"


def _signal_from_dict(d: dict) -> SocialTrendSignal:
    return SocialTrendSignal(
        signal_id=d["signal_id"],
        platform=d["platform"],
        topic=d["topic"],
        trend_score=float(d["trend_score"]),
        freshness_hours=float(d.get("freshness_hours", 0)),
        linked_categories=list(d.get("linked_categories", [])),
        linked_product_ids=list(d.get("linked_product_ids", [])),
        trend_uplift=float(d["trend_uplift"]),
        summary=d.get("summary", ""),
        source_post_ids=list(d.get("source_post_ids", [])),
        filtered_reason=d.get("filtered_reason", "latest_high_trend"),
    )


def _event_from_dict(d: dict) -> LocalEvent:
    return LocalEvent(
        canonical_event_id=d["canonical_event_id"],
        source=d["source"],
        source_event_id=d.get("source_event_id", ""),
        name=d["name"],
        start_at=d["start_at"],
        end_at=d.get("end_at"),
        venue_name=d.get("venue_name", ""),
        lat=float(d["lat"]),
        lon=float(d["lon"]),
        distance_km=float(d.get("distance_km", 0)),
        event_type=d.get("event_type", "festival"),
        event_impact_score=float(d.get("event_impact_score", 0.5)),
        affected_categories=list(d.get("affected_categories", [])),
        affected_product_ids=list(d.get("affected_product_ids", [])),
    )


def load_mock_trends(store_id: str) -> List[SocialTrendSignal]:
    if not os.path.exists(TRENDS_PATH):
        return []
    with open(TRENDS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    block = data.get(store_id, data.get("*", {}))
    return [_signal_from_dict(s) for s in block.get("signals", [])]


def load_mock_events(store_id: str) -> List[LocalEvent]:
    if not os.path.exists(EVENTS_PATH):
        return []
    with open(EVENTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    block = data.get(store_id, data.get("*", {}))
    return [_event_from_dict(e) for e in block.get("events", [])]

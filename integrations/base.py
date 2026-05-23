from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RawPost:
    id: str
    platform: str
    text: str
    hashtags: List[str]
    created_at: str
    metrics: dict = field(default_factory=dict)


@dataclass
class SocialTrendSignal:
    signal_id: str
    platform: str
    topic: str
    trend_score: float
    freshness_hours: float
    linked_categories: List[str]
    linked_product_ids: List[str]
    trend_uplift: float
    summary: str
    source_post_ids: List[str]
    filtered_reason: str = "latest_high_trend"


@dataclass
class LocalEvent:
    canonical_event_id: str
    source: str
    source_event_id: str
    name: str
    start_at: str
    end_at: Optional[str]
    venue_name: str
    lat: float
    lon: float
    distance_km: float
    event_type: str
    event_impact_score: float
    affected_categories: List[str]
    affected_product_ids: List[str] = field(default_factory=list)

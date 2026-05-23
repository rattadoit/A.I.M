import json
from typing import List, Tuple

import streamlit as st

from config import SETTINGS, SNS_KEYWORDS_FLAT, TRADE_AREA_RADIUS_KM
from integrations.base import LocalEvent, RawPost, SocialTrendSignal
from integrations.event_normalizer import dedupe_events, filter_events_by_date, score_event_impact
from integrations.events_eventbrite import load_eventbrite
from integrations.events_ode import load_ode
from integrations.events_ticketmaster import load_ticketmaster
from integrations.mock_loaders import load_mock_events, load_mock_trends
from integrations.sns_instagram import fetch_instagram
from integrations.sns_tiktok import fetch_tiktok
from integrations.sns_x import fetch_x
from integrations.trend_agent import score_and_filter_trends
from services.geocode import get_store_coords


def _collect_live_posts(region: str, since_hours: int) -> List[RawPost]:
    posts: List[RawPost] = []
    for fetcher in (fetch_x, fetch_instagram, fetch_tiktok):
        try:
            posts.extend(fetcher(region, SNS_KEYWORDS_FLAT, since_hours))
        except Exception:
            continue
    return posts


def _collect_live_events(
    lat: float,
    lon: float,
    trade_area: str,
    target_date: str,
) -> List[LocalEvent]:
    radius = TRADE_AREA_RADIUS_KM.get(trade_area, SETTINGS.EVENT_SEARCH_RADIUS_KM)
    events: List[LocalEvent] = []
    for loader in (load_ticketmaster, load_eventbrite, load_ode):
        try:
            events.extend(
                loader(lat, lon, radius, target_date, SETTINGS.EVENT_DAY_WINDOW)
            )
        except Exception:
            continue
    events = dedupe_events(events)
    events = filter_events_by_date(events, target_date, SETTINGS.EVENT_DAY_WINDOW)
    for e in events:
        e.event_impact_score = score_event_impact(e, trade_area)
    return events


def load_external_signals_impl(
    store_id: str,
    target_date: str,
    trade_area: str,
    region: str,
) -> Tuple[List[SocialTrendSignal], List[LocalEvent], str]:
    """Returns trends, events, status_message."""
    if SETTINGS.USE_MOCK_EXTERNAL:
        trends = load_mock_trends(store_id)
        events = load_mock_events(store_id)
        events = filter_events_by_date(events, target_date, SETTINGS.EVENT_DAY_WINDOW)
        for e in events:
            e.event_impact_score = score_event_impact(e, trade_area)
        return trends, events, "Mock 외부 신호 로드"

    raw_posts = _collect_live_posts(region, SETTINGS.TREND_MAX_AGE_HOURS)
    trends = score_and_filter_trends(
        store_id, region, trade_area, target_date, raw_posts, use_llm=True
    )
    lat, lon = get_store_coords(store_id)
    events = _collect_live_events(lat, lon, trade_area, target_date)

    if not trends and not events and not raw_posts:
        trends = load_mock_trends(store_id)
        events = load_mock_events(store_id)
        for e in events:
            e.event_impact_score = score_event_impact(e, trade_area)
        return trends, events, "API 미연동 — Mock 폴백"

    return trends, events, f"Live 수집 (posts={len(raw_posts)}, trends={len(trends)}, events={len(events)})"


@st.cache_data(ttl=3600, show_spinner=False)
def load_external_signals(
    store_id: str,
    target_date: str,
    trade_area: str,
    region: str,
) -> Tuple[List[SocialTrendSignal], List[LocalEvent], str]:
    return load_external_signals_impl(store_id, target_date, trade_area, region)


def signals_to_json(trends: List[SocialTrendSignal], events: List[LocalEvent]) -> str:
    from dataclasses import asdict

    return json.dumps(
        {
            "trends": [asdict(t) for t in trends],
            "events": [asdict(e) for e in events],
        },
        ensure_ascii=False,
        default=str,
    )

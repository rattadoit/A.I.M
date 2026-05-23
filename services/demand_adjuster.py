from typing import Dict, List, Tuple

from config import BASELINE_PRODUCTS, SETTINGS
from integrations.base import LocalEvent, SocialTrendSignal
from services.forecast_context import ExternalForecastContext


def build_product_uplift_maps(
    trends: List[SocialTrendSignal],
    events: List[LocalEvent],
    product_catalog: List[dict] = None,
    max_total: float = None,
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, str]]:
    product_catalog = product_catalog or BASELINE_PRODUCTS
    max_total = max_total if max_total is not None else SETTINGS.MAX_EXTERNAL_UPLIFT

    sns_by = {p["id"]: 0.0 for p in product_catalog}
    evt_by = {p["id"]: 0.0 for p in product_catalog}
    reasons = {p["id"]: "" for p in product_catalog}
    id_to_cat = {p["id"]: p["category"] for p in product_catalog}

    for t in trends:
        for pid in t.linked_product_ids or []:
            if pid in sns_by:
                sns_by[pid] += t.trend_uplift
        for p in product_catalog:
            if p["category"] in (t.linked_categories or []) and not t.linked_product_ids:
                sns_by[p["id"]] += t.trend_uplift * 0.5

    for e in events:
        weight = e.event_impact_score * 0.15
        for pid in e.affected_product_ids or []:
            if pid in evt_by:
                evt_by[pid] += weight
        for p in product_catalog:
            if p["category"] in (e.affected_categories or []) and not e.affected_product_ids:
                evt_by[p["id"]] += weight * 0.5

    for pid in sns_by:
        total = sns_by[pid] + evt_by[pid]
        if total > max_total:
            scale = max_total / total if total > 0 else 1.0
            sns_by[pid] *= scale
            evt_by[pid] *= scale
        parts = []
        if sns_by[pid] > 0:
            parts.append(f"SNS +{int(sns_by[pid] * 100)}%")
        if evt_by[pid] > 0:
            parts.append(f"행사 +{int(evt_by[pid] * 100)}%")
        reasons[pid] = " | ".join(parts)

    return sns_by, evt_by, reasons


def build_external_context(
    trends: List[SocialTrendSignal],
    events: List[LocalEvent],
) -> ExternalForecastContext:
    if not trends and not events:
        return ExternalForecastContext.empty()

    sns_by, evt_by, reason_snippets = build_product_uplift_maps(trends, events)
    trend_summaries = [f"[{t.platform}] {t.topic}: {t.summary}" for t in trends[:5]]
    event_summaries = [
        f"{e.name} ({e.distance_km:.1f}km, {e.start_at[:10]})"
        for e in events[:5]
    ]
    return ExternalForecastContext(
        sns_by_product=sns_by,
        event_by_product=evt_by,
        reason_snippets=reason_snippets,
        trend_summaries=trend_summaries,
        event_summaries=event_summaries,
        total_sns_uplift=sum(sns_by.values()),
        total_event_uplift=sum(evt_by.values()),
    )

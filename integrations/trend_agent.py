import json
import math
import os
import re
import uuid
from datetime import datetime, timezone
from typing import List

from config import BASELINE_PRODUCTS, SETTINGS, SNS_KEYWORDS_BY_CATEGORY
from integrations.base import RawPost, SocialTrendSignal

PRODUCT_NAME_TO_ID = {p["name"]: p["id"] for p in BASELINE_PRODUCTS}
CATEGORY_BY_PRODUCT = {p["id"]: p["category"] for p in BASELINE_PRODUCTS}


def _parse_hours_ago(created_at: str) -> float:
    try:
        if created_at.endswith("Z"):
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(created_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (now - dt).total_seconds() / 3600.0)
    except (ValueError, TypeError):
        return 0.0


def _match_products(text: str, hashtags: List[str]) -> tuple[List[str], List[str]]:
    blob = (text + " " + " ".join(hashtags)).lower()
    categories = set()
    product_ids = []
    for cat, keywords in SNS_KEYWORDS_BY_CATEGORY.items():
        for kw in keywords:
            if kw.lower() in blob:
                categories.add(cat)
    for p in BASELINE_PRODUCTS:
        if p["name"].lower() in blob:
            product_ids.append(p["id"])
            categories.add(p["category"])
    return list(categories), product_ids


def _rule_score(post: RawPost) -> float:
    views = float(post.metrics.get("views", 0) or post.metrics.get("impressions", 0) or 0)
    likes = float(post.metrics.get("likes", 0) or 0)
    retweets = float(post.metrics.get("retweets", 0) or 0)
    engagement = math.log1p(views) / 12.0 + math.log1p(likes + retweets * 2) / 8.0
    cats, pids = _match_products(post.text, post.hashtags)
    keyword_bonus = 0.15 if (cats or pids) else 0.0
    return min(1.0, engagement + keyword_bonus)


def _rule_based_signals(
    store_id: str,
    region: str,
    trade_area_type: str,
    target_date: str,
    raw_posts: List[RawPost],
) -> List[SocialTrendSignal]:
    signals = []
    for post in raw_posts:
        freshness = _parse_hours_ago(post.created_at)
        score = _rule_score(post)
        cats, pids = _match_products(post.text, post.hashtags)
        if not cats and not pids:
            continue
        uplift = min(0.15, round(score * 0.12, 3))
        topic = (post.text[:40] + "…") if len(post.text) > 40 else post.text
        signals.append(
            SocialTrendSignal(
                signal_id=str(uuid.uuid4())[:8],
                platform=post.platform,
                topic=topic or post.platform,
                trend_score=round(score, 3),
                freshness_hours=round(freshness, 1),
                linked_categories=cats,
                linked_product_ids=pids,
                trend_uplift=uplift,
                summary=f"[{post.platform}] {region}·{trade_area_type} 관련 언급 (점수 {score:.2f})",
                source_post_ids=[post.id],
                filtered_reason="rule_scorer",
            )
        )
    return signals


def _llm_signals(
    store_id: str,
    region: str,
    trade_area_type: str,
    target_date: str,
    raw_posts: List[RawPost],
) -> List[SocialTrendSignal]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not raw_posts:
        return []

    try:
        from openai import OpenAI
    except ImportError:
        return []

    client = OpenAI(api_key=api_key)
    sku_list = ", ".join(f"{p['id']}:{p['name']}" for p in BASELINE_PRODUCTS)
    payload = {
        "store_id": store_id,
        "region": region,
        "trade_area_type": trade_area_type,
        "target_date": target_date,
        "posts": [
            {
                "id": p.id,
                "platform": p.platform,
                "text": p.text[:500],
                "hashtags": p.hashtags,
                "metrics": p.metrics,
                "created_at": p.created_at,
            }
            for p in raw_posts[:30]
        ],
    }
    prompt = f"""편의점 발주 보조 AI입니다. 아래 SNS 게시물에서 수요에 실질 영향 있는 트렌드만 JSON 배열로 반환하세요.
SKU: {sku_list}
각 항목: signal_id, platform, topic, trend_score(0-1), freshness_hours, linked_categories, linked_product_ids, trend_uplift(0-0.15), summary, source_post_ids
score < {SETTINGS.TREND_SCORE_THRESHOLD} 또는 오래된 항목은 제외.

입력:
{json.dumps(payload, ensure_ascii=False)}"""

    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "Respond with JSON array only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        text = resp.choices[0].message.content or "[]"
        text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
        items = json.loads(text)
        if isinstance(items, dict):
            items = items.get("signals", [])
        out = []
        for d in items:
            out.append(
                SocialTrendSignal(
                    signal_id=d.get("signal_id", str(uuid.uuid4())[:8]),
                    platform=d.get("platform", "unknown"),
                    topic=d.get("topic", ""),
                    trend_score=float(d.get("trend_score", 0)),
                    freshness_hours=float(d.get("freshness_hours", 0)),
                    linked_categories=list(d.get("linked_categories", [])),
                    linked_product_ids=list(d.get("linked_product_ids", [])),
                    trend_uplift=float(d.get("trend_uplift", 0)),
                    summary=d.get("summary", ""),
                    source_post_ids=list(d.get("source_post_ids", [])),
                    filtered_reason="llm",
                )
            )
        return out
    except Exception:
        return []


def filter_trends(signals: List[SocialTrendSignal]) -> List[SocialTrendSignal]:
    filtered = [
        s
        for s in signals
        if s.freshness_hours <= SETTINGS.TREND_MAX_AGE_HOURS
        and s.trend_score >= SETTINGS.TREND_SCORE_THRESHOLD
    ]
    filtered.sort(key=lambda s: (s.trend_score, -s.freshness_hours), reverse=True)
    return filtered[: SETTINGS.TREND_TOP_K]


def score_and_filter_trends(
    store_id: str,
    region: str,
    trade_area_type: str,
    target_date: str,
    raw_posts: List[RawPost],
    use_llm: bool = True,
) -> List[SocialTrendSignal]:
    signals: List[SocialTrendSignal] = []
    if use_llm and os.getenv("OPENAI_API_KEY"):
        signals = _llm_signals(store_id, region, trade_area_type, target_date, raw_posts)
    if not signals:
        signals = _rule_based_signals(store_id, region, trade_area_type, target_date, raw_posts)
    return filter_trends(signals)

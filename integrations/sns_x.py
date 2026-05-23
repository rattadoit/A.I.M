import os
from datetime import datetime, timedelta, timezone
from typing import List

from integrations.base import RawPost

try:
    import httpx
except ImportError:
    httpx = None


def fetch_x(region: str, keywords: List[str], since_hours: int = 72) -> List[RawPost]:
    token = os.getenv("X_API_BEARER_TOKEN")
    if not token or not httpx:
        return []
    query = " OR ".join(keywords[:5]) + f" {region}"
    start_time = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "query": query,
        "max_results": 50,
        "start_time": start_time,
        "tweet.fields": "created_at,public_metrics",
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []

    posts = []
    for item in data.get("data", []):
        metrics = item.get("public_metrics", {})
        posts.append(
            RawPost(
                id=item["id"],
                platform="x",
                text=item.get("text", ""),
                hashtags=[],
                created_at=item.get("created_at", ""),
                metrics={
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "views": metrics.get("impression_count", 0),
                },
            )
        )
    return posts

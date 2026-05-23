import os
from typing import List

from integrations.base import RawPost

try:
    import httpx
except ImportError:
    httpx = None


def fetch_instagram(region: str, keywords: List[str], since_hours: int = 72) -> List[RawPost]:
    """Instagram Graph API — 해시태그 미디어 검색 (토큰·비즈니스 계정 필요)."""
    token = os.getenv("META_ACCESS_TOKEN") or os.getenv("IG_USER_ID")
    if not token or not httpx:
        return []
    # 실제 구현: graph.facebook.com/v18.0/{ig-user-id}/media 등
    return []

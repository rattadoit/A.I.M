import os
from typing import List

from integrations.base import RawPost

try:
    import httpx
except ImportError:
    httpx = None


def fetch_tiktok(region: str, keywords: List[str], since_hours: int = 72) -> List[RawPost]:
    """TikTok API — Research/Marketing API 자격 필요."""
    if not os.getenv("TIKTOK_CLIENT_KEY") or not httpx:
        return []
    return []

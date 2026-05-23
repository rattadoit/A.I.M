import os
from typing import Tuple

import pandas as pd

GEOCODE_PATH = "data/store_geocode.csv"
_coords_cache = None


def _load_geocode():
    global _coords_cache
    if _coords_cache is not None:
        return _coords_cache
    if os.path.exists(GEOCODE_PATH):
        df = pd.read_csv(GEOCODE_PATH)
        _coords_cache = {
            row["store_id"]: (float(row["lat"]), float(row["lon"]))
            for _, row in df.iterrows()
        }
    else:
        _coords_cache = {
            "S001": (37.5572, 126.9244),
            "S002": (37.5219, 126.9245),
            "S003": (37.5636, 126.9086),
        }
    return _coords_cache


def get_store_coords(store_id: str) -> Tuple[float, float]:
    return _load_geocode().get(store_id, (37.5665, 126.9780))

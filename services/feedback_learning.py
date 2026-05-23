from typing import Dict

import pandas as pd


def compute_owner_bias(feedback_df: pd.DataFrame) -> Dict[str, float]:
    """product_id -> median(owner - recommended), 정수 반올림."""
    if feedback_df is None or feedback_df.empty:
        return {}
    df = feedback_df.copy()
    df["delta"] = df["owner_adjusted_qty"] - df["recommended_order_qty"]
    bias = df.groupby("product_id")["delta"].median().round().astype(int).to_dict()
    return {k: float(v) for k, v in bias.items()}

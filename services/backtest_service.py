import datetime

import pandas as pd

from config import BASELINE_PRODUCTS
from logic import get_dynamic_safety_stock


def run_backtest(sales_df: pd.DataFrame, store_id: str, days: int = 60) -> pd.DataFrame:
    """
    과거 판매 이력 기반 단순 백테스트: naive 발주 vs AI 스타일(ML 없이 판매+안전재고) 비교.
    """
    df = sales_df[sales_df["store_id"] == store_id].copy()
    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])
    cutoff = df["date"].max() - datetime.timedelta(days=days)
    df = df[df["date"] >= cutoff]

    rows = []
    for date_val, day_df in df.groupby("date"):
        disposed = int(day_df["disposed_qty"].sum())
        sold_out = int((day_df["sold_out"] == 1).sum())
        sales_sum = int(day_df["sales_qty"].sum())

        naive_orders = 0
        ai_style_orders = 0
        for _, r in day_df.iterrows():
            stock = int(r["stock_qty"])
            sales = int(r["sales_qty"])
            naive_orders += max(0, sales - stock + max(1, int(sales * 0.2)))

            prod = next((p for p in BASELINE_PRODUCTS if p["id"] == r["product_id"]), None)
            if prod:
                safety = get_dynamic_safety_stock(
                    prod["shelf_life_type"], prod["disposal_risk"], float(sales)
                )
            else:
                safety = max(1, int(sales * 0.2))
            ai_style_orders += max(0, sales + safety - stock)

        rows.append(
            {
                "date": date_val.strftime("%Y-%m-%d"),
                "total_sales": sales_sum,
                "disposed_qty": disposed,
                "sold_out_count": sold_out,
                "naive_order_total": naive_orders,
                "ai_style_order_total": ai_style_orders,
            }
        )

    return pd.DataFrame(rows)

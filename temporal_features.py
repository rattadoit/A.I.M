"""
시간대·요일별 수요 예측 피처 엔진

편의점 상품은 시간대·요일·주말·공휴일에 따라 판매량이 달라지므로
아래 변수를 추출해 ML 수요 예측 및 발주 추천에 반영한다.

● hour, day_of_week, is_weekend, is_holiday
● previous_day_sales, previous_week_sales
● moving_average_7d, moving_average_28d
● 출근 / 점심 / 퇴근 / 야간 시간대별 수요
"""

import datetime
from typing import Optional

import pandas as pd

DAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]

# 출근·점심·퇴근·야간 (hour inclusive start, exclusive end)
COMMUTE_PERIODS = {
    "출근": (7, 11),
    "점심": (11, 14),
    "퇴근": (17, 20),
    "야간": (21, 24),
}

# 합성 데이터용 공휴일 (2026년, 분석 구간)
KOREAN_HOLIDAYS_2026 = {
    "2026-01-01", "2026-01-28", "2026-01-29", "2026-01-30",
    "2026-03-01", "2026-05-05", "2026-05-24", "2026-06-06",
    "2026-08-15", "2026-10-03", "2026-10-09",
    "2026-12-25",
}

# 레거시 6구간 (hourly CSV 합성용)
TIME_SLOTS = [
    ("새벽", 0, 6),
    ("아침", 6, 11),
    ("점심", 11, 14),
    ("오후", 14, 18),
    ("저녁", 18, 22),
    ("심야", 22, 24),
]

SLOT_BOUNDARIES = [(0, 3), (3, 6), (6, 9), (9, 12), (12, 15), (15, 18), (18, 21), (21, 24)]

DISTRICT_HOURLY_PROFILE = {
    "학교": {
        "weekday": {"default": [0.01, 0.04, 0.08, 0.22, 0.28, 0.22, 0.10, 0.05]},
        "weekend": {"default": [0.05, 0.08, 0.12, 0.18, 0.22, 0.20, 0.10, 0.05]},
        "products": {
            "컵라면": {"weekday": [0.01, 0.03, 0.06, 0.20, 0.35, 0.25, 0.08, 0.02]},
            "샌드위치": {"weekday": [0.02, 0.10, 0.15, 0.30, 0.28, 0.10, 0.04, 0.01]},
            "아이스크림": {"weekday": [0.02, 0.05, 0.10, 0.25, 0.35, 0.18, 0.04, 0.01]},
        },
    },
    "오피스": {
        "weekday": {"default": [0.01, 0.12, 0.18, 0.28, 0.22, 0.12, 0.05, 0.02]},
        "weekend": {"default": [0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.12, 0.05]},
        "products": {
            "아메리카노": {"weekday": [0.02, 0.22, 0.25, 0.25, 0.15, 0.08, 0.02, 0.01]},
            "도시락": {"weekday": [0.01, 0.05, 0.10, 0.45, 0.28, 0.08, 0.02, 0.01]},
            "샌드위치": {"weekday": [0.02, 0.15, 0.20, 0.30, 0.20, 0.10, 0.02, 0.01]},
        },
    },
    "주거지": {
        "weekday": {"default": [0.02, 0.06, 0.10, 0.18, 0.20, 0.28, 0.12, 0.04]},
        "weekend": {"default": [0.04, 0.08, 0.12, 0.18, 0.22, 0.24, 0.08, 0.04]},
        "products": {
            "맥주": {
                "weekday": [0.02, 0.02, 0.05, 0.10, 0.15, 0.38, 0.22, 0.06],
                "weekend": [0.03, 0.05, 0.08, 0.12, 0.18, 0.35, 0.14, 0.05],
            },
            "핫바": {
                "weekday": [0.02, 0.04, 0.08, 0.15, 0.20, 0.35, 0.12, 0.04],
                "weekend": [0.04, 0.06, 0.10, 0.15, 0.20, 0.30, 0.10, 0.05],
            },
            "도시락": {"weekday": [0.02, 0.05, 0.08, 0.15, 0.20, 0.35, 0.12, 0.03]},
            "컵라면": {
                "weekday": [0.03, 0.05, 0.08, 0.12, 0.18, 0.38, 0.12, 0.04],
                "weekend": [0.05, 0.08, 0.10, 0.15, 0.18, 0.32, 0.08, 0.04],
            },
        },
    },
}


def is_holiday(date_str: str) -> int:
    """공휴일 여부 (0/1)."""
    key = str(date_str)[:10]
    return 1 if key in KOREAN_HOLIDAYS_2026 else 0


def hour_to_time_slot(hour: int) -> str:
    for label, start, end in TIME_SLOTS:
        if start <= hour < end:
            return label
    return "심야"


def hour_in_period(hour: int, period_name: str) -> bool:
    start, end = COMMUTE_PERIODS[period_name]
    return start <= hour < end


def get_hourly_weights(district: str, product_name: str, day_type: str) -> list[float]:
    profile = DISTRICT_HOURLY_PROFILE.get(district, DISTRICT_HOURLY_PROFILE["주거지"])
    prod_profiles = profile.get("products", {})
    if product_name in prod_profiles:
        prod_cfg = prod_profiles[product_name]
        weights = prod_cfg.get(day_type, prod_cfg.get("weekday", profile[day_type]["default"]))
    else:
        weights = profile[day_type]["default"]
    total = sum(weights)
    return [w / total for w in weights]


def distribute_daily_sales_to_hours(
    sales_qty: int, district: str, product_name: str, day_of_week: int
) -> list[dict]:
    if sales_qty <= 0:
        return []
    day_type = "weekend" if day_of_week >= 5 else "weekday"
    weights = get_hourly_weights(district, product_name, day_type)
    rows = []
    remaining = sales_qty
    for i, (start_h, end_h) in enumerate(SLOT_BOUNDARIES):
        if i < len(weights) - 1:
            qty = int(round(sales_qty * weights[i]))
            remaining -= qty
        else:
            qty = max(0, remaining)
        if qty <= 0:
            continue
        mid_hour = min(23, (start_h + end_h) // 2)
        rows.append({
            "hour": mid_hour,
            "time_slot": hour_to_time_slot(mid_hour),
            "sales_qty": qty,
        })
    return rows


def build_hourly_sales_from_daily(
    sales_df: pd.DataFrame, store_df: pd.DataFrame, product_df: pd.DataFrame
) -> pd.DataFrame:
    store_map = store_df.set_index("store_id")["trade_area_type"].to_dict()
    product_map = product_df.set_index("product_id")["product_name"].to_dict()
    rows = []
    for _, row in sales_df.iterrows():
        date_obj = datetime.datetime.strptime(str(row["date"])[:10], "%Y-%m-%d")
        hourly_rows = distribute_daily_sales_to_hours(
            int(row["sales_qty"]),
            store_map.get(row["store_id"], "주거지"),
            product_map.get(row["product_id"], ""),
            date_obj.weekday(),
        )
        for hr in hourly_rows:
            rows.append({
                "date": row["date"],
                "store_id": row["store_id"],
                "product_id": row["product_id"],
                "hour": hr["hour"],
                "time_slot": hr["time_slot"],
                "sales_qty": hr["sales_qty"],
            })
    return pd.DataFrame(rows)


def _hist_slice(sales_df: pd.DataFrame, store_id: str, product_id: str, target) -> pd.DataFrame:
    df = sales_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    return df[
        (df["store_id"] == store_id)
        & (df["product_id"] == product_id)
        & (df["date"] < target)
    ].sort_values("date")


def compute_period_demands_from_hourly(
    hourly_df: pd.DataFrame,
    store_id: str,
    product_id: str,
    target_date_str: str,
) -> dict:
    """출근·점심·퇴근·야간 시간대별 예상 판매량(최근 14일 hourly 합산 비율)."""
    target = pd.to_datetime(target_date_str)
    h = hourly_df.copy()
    h["date"] = pd.to_datetime(h["date"])
    hsub = h[
        (h["store_id"] == store_id)
        & (h["product_id"] == product_id)
        & (h["date"] < target)
    ].tail(14 * 24)

    defaults = {k: 0.0 for k in COMMUTE_PERIODS}
    if hsub.empty:
        return defaults

    period_sales = {}
    for pname in COMMUTE_PERIODS:
        mask = hsub["hour"].apply(lambda x: hour_in_period(int(x), pname))
        period_sales[pname] = float(hsub.loc[mask, "sales_qty"].sum())

    total = sum(period_sales.values()) or 1.0
    daily_avg = hsub.groupby("date")["sales_qty"].sum().mean() if not hsub.empty else 10.0

    result = {}
    for pname, qty in period_sales.items():
        share = qty / total
        result[pname] = round(daily_avg * share, 1)
    return result


def compute_temporal_demand_features(
    sales_df: pd.DataFrame,
    store_id: str,
    product_id: str,
    target_date_str: str,
    hourly_df: Optional[pd.DataFrame] = None,
) -> dict:
    """
    명세 변수 전체를 계산한다.
    (target_date 당일 데이터는 제외 — 피처 누수 방지)
    """
    target = pd.to_datetime(target_date_str)
    date_obj = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
    day_of_week = date_obj.weekday()
    is_weekend = 1 if day_of_week >= 5 else 0
    is_holiday_flag = is_holiday(target_date_str)

    hist = _hist_slice(sales_df, store_id, product_id, target)

    if hist.empty:
        base = {
            "hour": 12,
            "day_of_week": day_of_week,
            "day_label": DAY_LABELS[day_of_week],
            "is_weekend": is_weekend,
            "is_holiday": is_holiday_flag,
            "previous_day_sales": 0.0,
            "previous_week_sales": 0.0,
            "moving_average_7d": 0.0,
            "moving_average_28d": 0.0,
            "demand_commute_morning": 0.0,
            "demand_lunch": 0.0,
            "demand_commute_evening": 0.0,
            "demand_night": 0.0,
            "peak_hour": 12,
            "peak_period": "점심",
            "temporal_applied": True,
            "temporal_reason": "이력 부족 — 기본 시간·요일 패턴",
            # 하위 호환
            "recent_7d_avg": 0.0,
            "recent_4w_weekday_avg": 0.0,
            "weekday_pattern_ratio": 1.0,
            "morning_ratio": 0.15,
            "lunch_ratio": 0.30,
            "evening_ratio": 0.25,
            "peak_time_slot": "점심",
        }
        return base

    previous_day_sales = float(hist.iloc[-1]["sales_qty"]) if len(hist) >= 1 else 0.0
    week_ago = target - pd.Timedelta(days=7)
    same_day = hist[hist["date"].dt.date == week_ago.date()]
    previous_week_sales = float(same_day.iloc[-1]["sales_qty"]) if not same_day.empty else previous_day_sales

    moving_average_7d = float(hist.tail(7)["sales_qty"].mean())
    moving_average_28d = float(hist.tail(28)["sales_qty"].mean()) if len(hist) >= 7 else moving_average_7d

    same_dow = hist[hist["date"].dt.weekday == day_of_week]
    recent_4w_weekday_avg = float(same_dow.tail(4)["sales_qty"].mean()) if not same_dow.empty else moving_average_7d
    weekday_pattern_ratio = round(recent_4w_weekday_avg / moving_average_7d, 3) if moving_average_7d > 0 else 1.0

    peak_hour = 12
    morning_ratio, lunch_ratio, evening_ratio = 0.15, 0.30, 0.25
    peak_time_slot = "점심"

    period_demands = {k: 0.0 for k in COMMUTE_PERIODS}
    if hourly_df is not None and not hourly_df.empty:
        period_demands = compute_period_demands_from_hourly(
            hourly_df, store_id, product_id, target_date_str
        )
        h = hourly_df.copy()
        h["date"] = pd.to_datetime(h["date"])
        hsub = h[
            (h["store_id"] == store_id)
            & (h["product_id"] == product_id)
            & (h["date"] < target)
        ].tail(14 * 24)
        if not hsub.empty:
            peak_hour = int(hsub.groupby("hour")["sales_qty"].sum().idxmax())
            total = hsub["sales_qty"].sum() or 1
            morning_ratio = hsub[hsub["hour"].between(6, 11)]["sales_qty"].sum() / total
            lunch_ratio = hsub[hsub["hour"].between(11, 14)]["sales_qty"].sum() / total
            evening_ratio = hsub[hsub["hour"].between(18, 24)]["sales_qty"].sum() / total
            peak_time_slot = hour_to_time_slot(peak_hour)

    peak_period = max(period_demands, key=period_demands.get) if any(period_demands.values()) else "점심"

    reason_parts = [
        f"hour={peak_hour}",
        f"요일={DAY_LABELS[day_of_week]}",
        f"MA7={moving_average_7d:.1f}",
        f"MA28={moving_average_28d:.1f}",
        f"피크={peak_period}",
    ]
    if is_weekend:
        reason_parts.append("주말")
    if is_holiday_flag:
        reason_parts.append("공휴일")

    return {
        "hour": peak_hour,
        "day_of_week": day_of_week,
        "day_label": DAY_LABELS[day_of_week],
        "is_weekend": is_weekend,
        "is_holiday": is_holiday_flag,
        "previous_day_sales": round(previous_day_sales, 1),
        "previous_week_sales": round(previous_week_sales, 1),
        "moving_average_7d": round(moving_average_7d, 2),
        "moving_average_28d": round(moving_average_28d, 2),
        "demand_commute_morning": period_demands.get("출근", 0.0),
        "demand_lunch": period_demands.get("점심", 0.0),
        "demand_commute_evening": period_demands.get("퇴근", 0.0),
        "demand_night": period_demands.get("야간", 0.0),
        "peak_hour": peak_hour,
        "peak_period": peak_period,
        "temporal_applied": True,
        "temporal_reason": " · ".join(reason_parts),
        "recent_7d_avg": round(moving_average_7d, 2),
        "recent_4w_weekday_avg": round(recent_4w_weekday_avg, 2),
        "weekday_pattern_ratio": weekday_pattern_ratio,
        "morning_ratio": round(morning_ratio, 3),
        "lunch_ratio": round(lunch_ratio, 3),
        "evening_ratio": round(evening_ratio, 3),
        "peak_time_slot": peak_time_slot,
    }


# 하위 호환 별칭
def compute_rolling_temporal_features(sales_df, store_id, product_id, target_date_str):
    return compute_temporal_demand_features(sales_df, store_id, product_id, target_date_str)


def get_trade_area_temporal_multiplier(
    district: str,
    product_name: str,
    day_of_week: int,
    peak_time_slot: Optional[str] = None,
    is_holiday_flag: int = 0,
) -> tuple[float, str]:
    """상권·요일·공휴일·시간대 패턴 보정 배수."""
    is_weekend = day_of_week >= 5
    mult = 1.0
    reasons = []

    if is_holiday_flag:
        mult *= 1.12
        reasons.append("공휴일 수요 변동")

    school_products = ["컵라면", "샌드위치", "아이스크림"]
    office_products = ["아메리카노", "도시락", "샌드위치"]
    residential_products = ["맥주", "핫바", "도시락", "컵라면"]

    if district == "학교":
        if product_name in school_products:
            mult *= 0.25 if is_weekend else 1.15
            reasons.append("학교 상권 주말 급감" if is_weekend else "학교 상권 평일 증가")
    elif district == "오피스":
        if product_name in office_products:
            mult *= 0.30 if is_weekend else 1.20
            if not is_weekend and product_name == "아메리카노":
                mult *= 1.08
                reasons.append("출근·점심 커피")
            elif not is_weekend and product_name == "도시락":
                mult *= 1.10
                reasons.append("점심 도시락")
            else:
                reasons.append("오피스 상권 패턴")
    elif district == "주거지":
        if product_name in residential_products:
            if is_weekend:
                mult *= 1.25
                reasons.append("주거 주말·저녁")
            if product_name == "맥주":
                mult *= 1.10
                reasons.append("야간 홈술")

    if peak_time_slot in ("점심",) and product_name in ["도시락", "샌드위치", "컵라면"]:
        mult *= 1.05

    return round(mult, 3), " + ".join(reasons) if reasons else ""


def get_holiday_demand_multiplier(is_holiday_flag: int) -> float:
    return 1.15 if is_holiday_flag else 1.0

"""
AI 발주 이상치 감지 모듈
점주 입력 발주량과 AI 추천 발주량 간 위험 편차를 탐지한다.
"""

from typing import Optional

FRESH_FOOD_SHELF_TYPE = "FF"
FRESH_FOOD_CATEGORY_LABEL = "Fresh Food"

PERCENT_THRESHOLD = 30
ABSOLUTE_THRESHOLD = 20
FRESH_FOOD_OVER_ORDER_MIN = 10
FRESH_FOOD_MEDIUM_BOOST = 10
FRESH_FOOD_HIGH_BOOST = 20

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


def is_fresh_food(item: dict) -> bool:
    """Fresh Food 여부: shelf_life_type FF 또는 category Fresh Food."""
    return (
        item.get("shelf_life_type") == FRESH_FOOD_SHELF_TYPE
        or item.get("category") == FRESH_FOOD_CATEGORY_LABEL
    )


def calc_diff_percent(predicted: int, actual: int) -> float:
    """AI 추천 대비 입력 발주량 변화율(%) 계산."""
    if predicted == 0:
        return 100.0 if actual != 0 else 0.0
    return round(((actual - predicted) / predicted) * 100, 1)


def calc_severity_from_percent(abs_diff_percent: float) -> Optional[str]:
    """차이율 기반 위험도 산출 (30% 이상일 때만 해당)."""
    if abs_diff_percent >= 100:
        return "high"
    if abs_diff_percent >= 50:
        return "medium"
    if abs_diff_percent >= PERCENT_THRESHOLD:
        return "low"
    return None


def max_severity(a: str, b: str) -> str:
    """두 위험도 중 더 높은 값 반환."""
    if SEVERITY_RANK.get(a, 0) >= SEVERITY_RANK.get(b, 0):
        return a
    return b


def fresh_food_severity_boost(absolute_diff: int, base_severity: str) -> str:
    """Fresh Food 과다 발주 시 최소 위험도 강제 상향."""
    severity = base_severity
    if absolute_diff >= FRESH_FOOD_HIGH_BOOST:
        severity = max_severity(severity, "high")
    elif absolute_diff >= FRESH_FOOD_MEDIUM_BOOST:
        severity = max_severity(severity, "medium")
    return severity


def build_warning_reason(
    is_ff: bool,
    fresh_food_warning: bool,
    abs_diff_percent: float,
    abs_absolute_diff: int,
) -> str:
    """팝업 표시용 경고 사유 문자열 생성."""
    if fresh_food_warning:
        return "Fresh food over-order risk"
    if abs_absolute_diff >= ABSOLUTE_THRESHOLD and abs_diff_percent >= PERCENT_THRESHOLD:
        return "Large absolute and percentage deviation from AI recommendation"
    if abs_absolute_diff >= ABSOLUTE_THRESHOLD:
        return "Absolute quantity deviation exceeds threshold"
    return "Percentage deviation exceeds threshold"


def is_anomaly(predicted: int, actual: int, is_ff: bool) -> tuple[bool, bool]:
    """
    이상치 여부 판정.
    Returns: (is_anomaly, fresh_food_warning)
    """
    absolute_diff = actual - predicted
    abs_absolute_diff = abs(absolute_diff)
    abs_diff_percent = abs(calc_diff_percent(predicted, actual))

    fresh_food_warning = False

    # 기본 규칙: ±30% 또는 절대 20개 이상
    basic_anomaly = (
        abs_diff_percent >= PERCENT_THRESHOLD
        or abs_absolute_diff >= ABSOLUTE_THRESHOLD
    )

    # Fresh Food: AI 추천 대비 +10개 이상 증가 시 무조건 경고
    if is_ff and absolute_diff >= FRESH_FOOD_OVER_ORDER_MIN:
        fresh_food_warning = True
        return True, fresh_food_warning

    return basic_anomaly, fresh_food_warning


def detect_order_anomalies(orders: list[dict]) -> list[dict]:
    """
    발주 항목 목록에서 이상치 상품 탐지.

    orders 각 항목 예시:
    {
        "product_id": "P01",
        "product": "삼각김밥",
        "category": "식사",
        "shelf_life_type": "FF",
        "predicted": 12,
        "actual": 25,
    }

    Returns:
        이상치 상품 dict 리스트 (severity, reason 등 포함)
    """
    anomalies = []

    for item in orders:
        predicted = int(item["predicted"])
        actual = int(item["actual"])
        ff = is_fresh_food(item)

        anomaly_flag, fresh_food_warning = is_anomaly(predicted, actual, ff)
        if not anomaly_flag:
            continue

        absolute_diff = actual - predicted
        abs_absolute_diff = abs(absolute_diff)
        diff_percent = calc_diff_percent(predicted, actual)
        abs_diff_percent = abs(diff_percent)

        # 퍼센트 기반 severity (기본값 low)
        severity = calc_severity_from_percent(abs_diff_percent) or "low"

        # Fresh Food 위험도 강화 (과다 발주 시)
        if ff and absolute_diff > 0:
            severity = fresh_food_severity_boost(absolute_diff, severity)

        display_category = FRESH_FOOD_CATEGORY_LABEL if ff else item.get("category", "")

        anomalies.append({
            "product_id": item.get("product_id", ""),
            "product": item["product"],
            "category": display_category,
            "predicted": predicted,
            "actual": actual,
            "diff_percent": diff_percent,
            "absolute_diff": absolute_diff,
            "severity": severity,
            "fresh_food_warning": fresh_food_warning or ff,
            "reason": build_warning_reason(
                ff, fresh_food_warning, abs_diff_percent, abs_absolute_diff
            ),
        })

    # High → Medium → Low 순 정렬
    anomalies.sort(key=lambda x: SEVERITY_RANK.get(x["severity"], 0), reverse=True)
    return anomalies


def validate_promotion_data(product_df) -> list[str]:
    """
    Validates promotion fields in the product master dataframe.
    Returns a list of validation error/warning messages.
    """
    import pandas as pd
    from datetime import datetime
    
    errors = []
    required_cols = [
        "original_price", "discount_price", "discount_rate", 
        "promotion_type", "is_1plus1", "is_2plus1", 
        "promotion_start_date", "promotion_end_date"
    ]
    
    for col in required_cols:
        if col not in product_df.columns:
            errors.append(f"필수 프로모션 컬럼 누락: '{col}'")
            
    if errors:
        return errors  # Stop further checks if core columns are missing
        
    for index, row in product_df.iterrows():
        p_id = row.get("product_id", f"Row_{index}")
        p_name = row.get("product_name", f"상품_{p_id}")
        
        orig = float(row["original_price"])
        disc = float(row["discount_price"])
        rate = float(row["discount_rate"])
        promo_type = str(row["promotion_type"])
        
        # 1. Price validation
        if orig < 0:
            errors.append(f"[{p_name}] 원가 오류: 원가 {orig}원은 0보다 작을 수 없습니다.")
        if disc < 0:
            errors.append(f"[{p_name}] 할인가 오류: 할인가 {disc}원은 0보다 작을 수 없습니다.")
        if disc > orig:
            errors.append(f"[{p_name}] 가격 무결성 오류: 할인가 {disc}원이 원가 {orig}원보다 큽니다.")
            
        # 2. Discount rate check
        if orig > 0:
            expected_rate = round((orig - disc) / orig, 2)
            # check rate with delta margin of 0.05
            if abs(rate - expected_rate) > 0.05 and promo_type != "None" and promo_type != "nan" and promo_type != "":
                errors.append(f"[{p_name}] 할인율 불일치: 입력값 {rate*100:.1f}%, 계산값 {expected_rate*100:.1f}%")
                
        # 3. Date validation
        start_date = str(row["promotion_start_date"])
        end_date = str(row["promotion_end_date"])
        
        if promo_type != "None" and promo_type != "nan" and promo_type != "":
            s_dt = None
            e_dt = None
            
            # Check start date
            try:
                s_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                errors.append(f"[{p_name}] 날짜 형식 오류: 시작일 '{start_date}'은 YYYY-MM-DD 형식이어야 합니다.")
                
            # Check end date
            try:
                e_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                errors.append(f"[{p_name}] 날짜 형식 오류: 종료일 '{end_date}'은 YYYY-MM-DD 형식이어야 합니다.")
                
            if s_dt and e_dt and s_dt > e_dt:
                errors.append(f"[{p_name}] 날짜 무결성 오류: 시작일 '{start_date}'이 종료일 '{end_date}'보다 늦습니다.")
                
    return errors

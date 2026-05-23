import os
import datetime
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from config import BASELINE_PRODUCTS
from temporal_features import (
    compute_temporal_demand_features,
    get_trade_area_temporal_multiplier,
    get_holiday_demand_multiplier,
    build_hourly_sales_from_daily,
    DAY_LABELS,
)

# Paths for CSV files
PRODUCT_CSV = "data/sample_product.csv"
STORE_CSV = "data/sample_store.csv"
WEATHER_CSV = "data/sample_weather.csv"
SALES_CSV = "data/sample_sales.csv"
HOURLY_SALES_CSV = "data/sample_hourly_sales.csv"

LOCATION_DEFAULTS = {
    "latitude": 37.5665,
    "longitude": 126.9780,
    "address": "서울시 샘플 주소",
    "school_count": 0,
    "hospital_count": 0,
    "office_count": 0,
    "subway_distance": 800,
    "commercial_density": 0.5,
    "residential_ratio": 0.5,
    "store_area_type": "일반상권",
}

LOCATION_NUMERIC_FEATURES = [
    "school_count",
    "hospital_count",
    "office_count",
    "subway_distance",
    "commercial_density",
    "residential_ratio",
]

class PredictionEngine:
    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.feature_cols = [
            "temperature", "humidity", "rainy", "rainfall",
            "hour", "day_of_week", "is_weekend", "is_holiday",
            "previous_day_sales", "previous_week_sales",
            "moving_average_7d", "moving_average_28d",
            "commute_morning_share", "lunch_share", "commute_evening_share", "night_share",
            "cat_encoded", "dist_encoded", "area_encoded", "prod_encoded",
            *LOCATION_NUMERIC_FEATURES,
        ]
        self.sales_df = None
        self.weather_df = None
        self.product_df = None
        self.store_df = None
        self.hourly_sales_df = None

    def ensure_hourly_sales_loaded(self):
        """캐시된 구버전 엔진 등 hourly_sales_df가 없을 때 보완 로드."""
        if getattr(self, "hourly_sales_df", None) is not None:
            return
        if self.sales_df is None:
            self.load_data()
            return
        if os.path.exists(HOURLY_SALES_CSV):
            self.hourly_sales_df = pd.read_csv(HOURLY_SALES_CSV)
            self.hourly_sales_df["date"] = pd.to_datetime(self.hourly_sales_df["date"])
        else:
            self.hourly_sales_df = build_hourly_sales_from_daily(
                self.sales_df, self.store_df, self.product_df
            )
            os.makedirs("data", exist_ok=True)
            self.hourly_sales_df.to_csv(HOURLY_SALES_CSV, index=False, encoding="utf-8-sig")
        
    def load_data(self):
        """Loads and pre-processes files, computing rolling averages for ML training."""
        if not (os.path.exists(PRODUCT_CSV) and os.path.exists(STORE_CSV) and 
                os.path.exists(WEATHER_CSV) and os.path.exists(SALES_CSV)):
            # If files are missing, run data generator
            from data_generator import generate_synthesized_data
            generate_synthesized_data()
            
        self.product_df = pd.read_csv(PRODUCT_CSV)
        self.store_df = pd.read_csv(STORE_CSV)
        self.weather_df = pd.read_csv(WEATHER_CSV)
        self.sales_df = pd.read_csv(SALES_CSV)
        self.hourly_sales_df = None

        self.store_df = self.ensure_location_features(self.store_df)
        
        # Parse dates
        self.sales_df["date"] = pd.to_datetime(self.sales_df["date"])
        self.weather_df["date"] = pd.to_datetime(self.weather_df["date"])

        # 시간대별 판매 이력 로드 (없으면 일별 데이터에서 합성)
        if os.path.exists(HOURLY_SALES_CSV):
            self.hourly_sales_df = pd.read_csv(HOURLY_SALES_CSV)
            self.hourly_sales_df["date"] = pd.to_datetime(self.hourly_sales_df["date"])
        else:
            self.hourly_sales_df = build_hourly_sales_from_daily(
                self.sales_df, self.store_df, self.product_df
            )
            os.makedirs("data", exist_ok=True)
            self.hourly_sales_df.to_csv(HOURLY_SALES_CSV, index=False, encoding="utf-8-sig")

    def ensure_location_features(self, store_df):
        """Adds prototype location columns when older sample data is loaded."""
        df = store_df.copy()
        for col, default in LOCATION_DEFAULTS.items():
            if col not in df.columns:
                df[col] = default

        for col in LOCATION_NUMERIC_FEATURES:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(LOCATION_DEFAULTS[col])

        df["store_area_type"] = df["store_area_type"].fillna(LOCATION_DEFAULTS["store_area_type"]).astype(str)
        df["address"] = df["address"].fillna(LOCATION_DEFAULTS["address"]).astype(str)
        return df
        
    def engineer_features(self):
        """Engineers rolling historical averages and encoders for Random Forest training."""
        # 1. Merge all info
        df = self.sales_df.merge(self.store_df, on="store_id", how="left")
        df = df.merge(self.product_df, on="product_id", how="left")
        
        # Merge weather
        df = df.merge(self.weather_df, on="date", how="left")
        
        # Date parts — 시간·요일·공휴일 피처
        from temporal_features import is_holiday
        df["day_of_week"] = df["date"].dt.weekday
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        df["is_holiday"] = df["date"].dt.strftime("%Y-%m-%d").apply(is_holiday)

        df = df.sort_values(by=["store_id", "product_id", "date"])
        g = df.groupby(["store_id", "product_id"])["sales_qty"]

        df["previous_day_sales"] = g.shift(1)
        df["previous_week_sales"] = g.shift(7)
        df["moving_average_7d"] = g.transform(lambda x: x.shift(1).rolling(7, min_periods=1).mean())
        df["moving_average_28d"] = g.transform(lambda x: x.shift(1).rolling(28, min_periods=1).mean())

        fill_val = df["sales_qty"].mean()
        for col in ["previous_day_sales", "previous_week_sales", "moving_average_7d", "moving_average_28d"]:
            df[col] = df[col].fillna(fill_val)

        df["hour"] = 12
        df["commute_morning_share"] = 0.15
        df["lunch_share"] = 0.30
        df["commute_evening_share"] = 0.20
        df["night_share"] = 0.15

        if self.hourly_sales_df is not None and not self.hourly_sales_df.empty:
            h = self.hourly_sales_df.copy()
            h["date"] = pd.to_datetime(h["date"])
            from temporal_features import hour_in_period

            def _period_share(frame, period):
                mask = frame["hour"].apply(lambda x: hour_in_period(int(x), period))
                return frame[mask].groupby(["store_id", "product_id", "date"])["sales_qty"].sum()

            totals = h.groupby(["store_id", "product_id", "date"])["sales_qty"].sum().reset_index(name="day_total")
            m = _period_share(h, "출근").reset_index(name="m_qty")
            l = _period_share(h, "점심").reset_index(name="l_qty")
            ev = _period_share(h, "퇴근").reset_index(name="e_qty")
            n = _period_share(h, "야간").reset_index(name="n_qty")
            by_hour = h.groupby(["store_id", "product_id", "date", "hour"])["sales_qty"].sum().reset_index()
            ph = (
                by_hour.sort_values("sales_qty", ascending=False)
                .groupby(["store_id", "product_id", "date"], as_index=False)
                .first()[["store_id", "product_id", "date", "hour"]]
            )

            slot_df = totals.merge(m, how="left").merge(l, how="left").merge(ev, how="left").merge(n, how="left").merge(ph, how="left")
            slot_df = slot_df.fillna(0)
            slot_df["day_total"] = slot_df["day_total"].replace(0, 1)
            slot_df["commute_morning_share"] = slot_df["m_qty"] / slot_df["day_total"]
            slot_df["lunch_share"] = slot_df["l_qty"] / slot_df["day_total"]
            slot_df["commute_evening_share"] = slot_df["e_qty"] / slot_df["day_total"]
            slot_df["night_share"] = slot_df["n_qty"] / slot_df["day_total"]
            slot_df = slot_df[["store_id", "product_id", "date", "hour", "commute_morning_share", "lunch_share", "commute_evening_share", "night_share"]]

            df = df.drop(columns=["hour", "commute_morning_share", "lunch_share", "commute_evening_share", "night_share"], errors="ignore")
            df = df.merge(slot_df, on=["store_id", "product_id", "date"], how="left")
            for col in ["hour", "commute_morning_share", "lunch_share", "commute_evening_share", "night_share"]:
                df[col] = df.groupby(["store_id", "product_id"])[col].shift(1)
            df["hour"] = df["hour"].fillna(12).astype(int)
            for col in ["commute_morning_share", "lunch_share", "commute_evening_share", "night_share"]:
                df[col] = df[col].fillna(0.2)
        
        # 3. Label Encoding
        for col, new_col in [
            ("category", "cat_encoded"),
            ("trade_area_type", "dist_encoded"),
            ("store_area_type", "area_encoded"),
            ("product_id", "prod_encoded"),
        ]:
            le = LabelEncoder()
            df[new_col] = le.fit_transform(df[col])
            self.label_encoders[col] = le
            
        return df

    def train_model(self):
        """Trains the Random Forest demand forecast model."""
        self.load_data()
        df = self.engineer_features()
        
        X = df[self.feature_cols]
        y = df["sales_qty"]
        
        # Standard RF setup
        self.model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42)
        self.model.fit(X, y)
        print("Machine learning model training complete! Score:", round(self.model.score(X, y), 4))
        
    def predict_ml_demand(self, target_date_str, store_id, weather_label, temp, humidity, rainfall, is_rainy):
        """Predicts sales using the trained Random Forest regressor."""
        if self.model is None:
            self.train_model()
        self.ensure_hourly_sales_loaded()
            
        date_obj = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
        day_of_week = date_obj.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0
        
        store_row = self.store_df[self.store_df["store_id"] == store_id].iloc[0]
        district = store_row["trade_area_type"]
        area_type = store_row["store_area_type"]
        
        predictions = []
        
        for p in BASELINE_PRODUCTS:
            p_id = p["id"]
            category = p["category"]
            
            # Encode categories
            cat_enc = self.label_encoders["category"].transform([category])[0]
            dist_enc = self.label_encoders["trade_area_type"].transform([district])[0]
            area_enc = self.label_encoders["store_area_type"].transform([area_type])[0]
            prod_enc = self.label_encoders["product_id"].transform([p_id])[0]
            
            # Fetch rolling history for this store/product up to the latest date
            sub_sales = self.sales_df[(self.sales_df["store_id"] == store_id) & (self.sales_df["product_id"] == p_id)]
            
            temporal = compute_temporal_demand_features(
                self.sales_df, store_id, p_id, target_date_str, self.hourly_sales_df
            )
            feature_values = {
                "temperature": temp,
                "humidity": humidity,
                "rainy": is_rainy,
                "rainfall": rainfall,
                "hour": temporal["hour"],
                "day_of_week": temporal["day_of_week"],
                "is_weekend": temporal["is_weekend"],
                "is_holiday": temporal["is_holiday"],
                "previous_day_sales": temporal["previous_day_sales"],
                "previous_week_sales": temporal["previous_week_sales"],
                "moving_average_7d": temporal["moving_average_7d"] or p["base_sales"],
                "moving_average_28d": temporal["moving_average_28d"] or p["base_sales"],
                "commute_morning_share": temporal["morning_ratio"],
                "lunch_share": temporal["lunch_ratio"],
                "commute_evening_share": temporal["evening_ratio"] * 0.6,
                "night_share": temporal["evening_ratio"] * 0.4,
                "cat_encoded": cat_enc,
                "dist_encoded": dist_enc,
                "area_encoded": area_enc,
                "prod_encoded": prod_enc,
            }
            for col in LOCATION_NUMERIC_FEATURES:
                feature_values[col] = float(store_row[col])

            features = pd.DataFrame([feature_values], columns=self.feature_cols)
            
            pred_qty = round(float(self.model.predict(features)[0]), 1)
            predictions.append((p_id, pred_qty))
            
        return dict(predictions)

def get_location_demand_factor(product_name, category, store_row):
    """Computes a readable prototype demand factor from sample location features."""
    school_count = float(store_row.get("school_count", 0))
    hospital_count = float(store_row.get("hospital_count", 0))
    office_count = float(store_row.get("office_count", 0))
    subway_distance = float(store_row.get("subway_distance", 800))
    commercial_density = float(store_row.get("commercial_density", 0.5))
    residential_ratio = float(store_row.get("residential_ratio", 0.5))

    factor = 1.0
    reasons = []

    commercial_bonus = commercial_density * 0.08
    factor += commercial_bonus
    if commercial_density >= 0.75:
        reasons.append("상업시설 밀도 높음")

    if subway_distance <= 250:
        factor += 0.08
        reasons.append("지하철 초근접")
    elif subway_distance <= 500:
        factor += 0.04
        reasons.append("지하철 접근성 양호")

    if product_name in ["컵라면", "샌드위치", "아이스크림", "핫바"]:
        bonus = min(school_count * 0.025, 0.18)
        factor += bonus
        if school_count >= 3:
            reasons.append("학교 밀집")

    if product_name in ["아메리카노", "도시락", "샌드위치"]:
        bonus = min(office_count * 0.012, 0.22)
        factor += bonus
        if office_count >= 10:
            reasons.append("오피스 밀집")

    if product_name in ["생수", "도시락", "아메리카노"]:
        bonus = min(hospital_count * 0.018, 0.12)
        factor += bonus
        if hospital_count >= 3:
            reasons.append("병원 접근성")

    if product_name in ["맥주", "핫바", "도시락", "컵라면"]:
        factor += residential_ratio * 0.12
        if residential_ratio >= 0.65:
            reasons.append("주거 배후수요")

    if category == "음료":
        factor += commercial_density * 0.04

    reason = " + ".join(reasons)
    return round(factor, 3), reason

def calculate_rule_forecast(weather, store_row, day_of_week):
    """
    Computes baseline heuristic rule sales.
    Replicates the base sales heuristics from original code, adding weekend dampeners.
    """
    is_weekend = 1 if day_of_week >= 5 else 0
    district = store_row["trade_area_type"]
    forecast_results = []
    
    for p in BASELINE_PRODUCTS:
        w_mult = 1.0
        d_mult = 1.0
        reasons = []
        
        # Weather rules
        if weather == "비":
            if p["name"] == "우산":
                w_mult = 10.0
                reasons.append("🌧️ 우산 수요 폭발 (+900%)")
            elif p["name"] == "컵라면":
                w_mult = 1.1
                reasons.append("🍜 뜨거운 국물류 선호 (+10%)")
            elif p["name"] == "도시락":
                w_mult = 1.2
                reasons.append("🍱 편의점 내 간편식 선호 (+20%)")
            elif p["name"] == "아이스크림":
                w_mult = 0.5
                reasons.append("🍦 차가운 간식 기피 (-50%)")
        elif weather == "폭염":
            if p["name"] == "얼음컵":
                w_mult = 3.5
                reasons.append("🧊 얼음컵 수요 급증 (+250%)")
            elif p["name"] == "생수":
                w_mult = 3.0
                reasons.append("💧 생수 갈증 해소 수요 (+200%)")
            elif p["name"] == "아메리카노":
                w_mult = 2.5
                reasons.append("☕ 아이스 아메리카노 선호 (+150%)")
            elif p["name"] == "아이스크림":
                w_mult = 2.0
                reasons.append("🍦 빙과류 판매 급증 (+100%)")
            elif p["name"] == "컵라면":
                w_mult = 0.6
                reasons.append("🍜 뜨거운 면류 기피 (-40%)")
        elif weather == "맑음":
            if p["name"] == "아이스크림":
                w_mult = 1.5
                reasons.append("☀️ 빙과류 일반 구매 증가 (+50%)")
            elif p["name"] == "맥주":
                w_mult = 1.2
                reasons.append("🍺 야외 활동 및 시원한 주류 선호 (+20%)")
                
        # Commercial District rules
        if district == "학교":
            if p["name"] == "컵라면":
                d_mult = 1.7
                reasons.append("🏫 학생 간식 소비 폭발 (+70%)")
            elif p["name"] == "샌드위치":
                d_mult = 1.8
                reasons.append("🥪 등하교 간편 식사 대용 (+80%)")
            elif p["name"] == "아이스크림":
                d_mult = 1.5
                reasons.append("🏫 학생 대상 디저트 선호 (+50%)")
        elif district == "오피스":
            if p["name"] == "아메리카노":
                d_mult = 2.5
                reasons.append("💼 직장인 피로 해소 커피 수요 (+150%)")
            elif p["name"] == "도시락":
                d_mult = 1.6
                reasons.append("💼 바쁜 직장인 점심 대용 (+60%)")
            elif p["name"] == "샌드위치":
                d_mult = 1.5
                reasons.append("💼 아침식사 및 오후 가벼운 간식 (+50%)")
        elif district == "주거지":
            if p["name"] == "맥주":
                d_mult = 2.0
                reasons.append("🏠 퇴근 후 홈술 맥주 수요 (+100%)")
            elif p["name"] == "핫바":
                d_mult = 1.5
                reasons.append("🍢 아이들 간식 및 야식용 핫바 (+50%)")
            elif p["name"] == "도시락":
                d_mult = 1.2
                reasons.append("🏠 1인 가구 간편 저녁 식사 (+20%)")
                
        # Weekend adjustment (Office and School drop, Residential raises)
        weekend_mult = 1.0
        if is_weekend:
            if district == "오피스":
                weekend_mult = 0.3
                reasons.append("📅 오피스 상권 주말 수요 감소 (-70%)")
            elif district == "학교":
                weekend_mult = 0.2
                reasons.append("📅 대학 상권 주말 수요 급감 (-80%)")
            elif district == "주거지":
                if p["name"] == "맥주":
                    weekend_mult = 1.3
                    reasons.append("🍺 주거지 주말 홈술 수요 증가 (+30%)")
                else:
                    weekend_mult = 1.1
        else:
            if district in ["오피스", "학교"]:
                weekend_mult = 1.1
                
        location_mult, location_reason = get_location_demand_factor(p["name"], p["category"], store_row)
        if location_reason:
            reasons.append(f"샘플 위치 피처 반영: {location_reason} ({location_mult:.2f}x)")

        expected_sales = round(p["base_sales"] * w_mult * d_mult * weekend_mult * location_mult, 1)
        reason_str = " + ".join(reasons) if reasons else "기본 안정 수요 흐름 유지"
        
        forecast_results.append({
            "id": p["id"],
            "expected_sales": expected_sales,
            "reason": reason_str,
            "w_mult": w_mult,
            "d_mult": d_mult,
            "location_mult": location_mult,
            "weekend_mult": weekend_mult
        })
        
    return {item["id"]: item for item in forecast_results}

def get_dynamic_safety_stock(shelf_life, disposal_risk, expected_sales):
    """
    Computes custom safety stock levels based on product shelf life and disposal risks.
    - HIGH risk (Fresh Foods): Tight safety margins to avoid heavy waste/write-offs.
    - MEDIUM risk: Moderate safety stocks.
    - LOW risk (Dry goods/Beverages): Higher safety stock to capture all sales and prevent stockouts.
    - Capped at maximum 40 units to prevent backroom overstocking.
    """
    if shelf_life == "FF":
        if disposal_risk == "HIGH":
            # Very tight safety margin (15% of expected sales)
            val = max(1, int(round(expected_sales * 0.15)))
        else:
            # Medium disposal risk (30% of expected sales)
            val = max(2, int(round(expected_sales * 0.30)))
    else:
        # Long shelf life, dry products (60% of expected sales)
        val = max(3, int(round(expected_sales * 0.60)))
        
    return min(40, val)

def get_continuous_weather_factor(product_name, temp, humidity, rainfall):
    """
    Computes a continuous weather-sensitivity adjustment factor for each product
    based on exact temperature, humidity, and rainfall.
    """
    factor = 1.0
    
    if product_name == "도시락":
        # Prefers indoors when raining (increases with rainfall)
        # Appetite drops slightly in extreme heat
        rain_bonus = 1.0 + (rainfall * 0.015)  # +1.5% per 1mm rain
        heat_penalty = 1.0
        if temp > 28.0:
            heat_penalty = 1.0 - (temp - 28.0) * 0.02  # -2% per 1C over 28C
        factor = rain_bonus * heat_penalty
        
    elif product_name == "아메리카노":
        # Hot weather increases iced drink demand smoothly, cold decreases
        # High humidity also increases it slightly
        temp_factor = 1.0 + (temp - 20.0) * 0.035  # +3.5% per 1C over 20C, negative for cold
        humidity_factor = 1.0 + (humidity - 50.0) * 0.003
        factor = temp_factor * humidity_factor
        
    elif product_name == "우산":
        # Ultra-conservative logarithmic saturation to model highly restricted physical store limits
        if rainfall > 0.0:
            import math
            factor = 1.0 + 0.45 * math.log(1.0 + rainfall)  # scales gentler, maxing out at 3.0x under 80mm rain
        else:
            factor = 1.0
            
    elif product_name == "생수":
        # Increases with temp and humidity
        temp_factor = 1.0 + (temp - 20.0) * 0.04  # +4% per 1C
        humidity_factor = 1.0 + (humidity - 50.0) * 0.004
        factor = temp_factor * humidity_factor
        
    elif product_name == "얼음컵":
        # Extremely sensitive to temp and humidity
        temp_factor = 1.0 + (temp - 20.0) * 0.06  # +6% per 1C
        humidity_factor = 1.0 + (humidity - 50.0) * 0.005
        factor = temp_factor * humidity_factor
        
    elif product_name == "컵라면":
        # Prefers cold slightly, rain bonus capped at a very realistic 10%
        temp_factor = 1.0 - (temp - 20.0) * 0.01  # gentler slope: -1% per 1C
        rain_bonus = 1.0 + min(0.1, rainfall * 0.005)  # +0.5% per 1mm, capped at +10% max
        factor = temp_factor * rain_bonus
        
    elif product_name == "샌드위치":
        # Stable, drops slightly in heat
        heat_penalty = 1.0
        if temp > 28.0:
            heat_penalty = 1.0 - (temp - 28.0) * 0.01
        factor = heat_penalty
        
    elif product_name == "맥주":
        # Increases with temp, drops slightly with rain
        temp_factor = 1.0 + (temp - 20.0) * 0.03
        rain_penalty = 1.0 - (rainfall * 0.008)
        factor = temp_factor * max(0.5, rain_penalty)
        
    elif product_name == "아이스크림":
        # Increases with temp, drops with rain
        temp_factor = 1.0 + (temp - 20.0) * 0.04
        rain_penalty = 1.0 - (rainfall * 0.015)
        factor = temp_factor * max(0.3, rain_penalty)
        
    elif product_name == "핫바":
        # Warm snack, likes cold and rain
        temp_factor = 1.0 - (temp - 20.0) * 0.015
        rain_bonus = 1.0 + (rainfall * 0.01)
        factor = temp_factor * rain_bonus
        
    return max(0.15, factor)  # floor at 15% to prevent negative or zero sales

def is_promotion_active(target_date_str, start_str, end_str):
    if not start_str or not end_str or pd.isna(start_str) or pd.isna(end_str):
        return False
    start_str = str(start_str).strip()
    end_str = str(end_str).strip()
    if start_str.lower() in ["none", "nan", ""] or end_str.lower() in ["none", "nan", ""]:
        return False
    try:
        target = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        start = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
        return start <= target <= end
    except Exception:
        return False

def get_top_products(period='daily'):
    """
    Retrieves Top 10 products based on sales quantity for the given period.
    - daily: sales on the latest date in history
    - weekly: sales over the last 7 days in history
    - monthly: sales over the last 30 days in history
    """
    sales_csv = "data/sample_sales.csv"
    product_csv = "data/sample_product.csv"
    if not os.path.exists(sales_csv) or not os.path.exists(product_csv):
        return pd.DataFrame()
        
    sales_df = pd.read_csv(sales_csv)
    product_df = pd.read_csv(product_csv)
    
    sales_df["date"] = pd.to_datetime(sales_df["date"])
    max_date = sales_df["date"].max()
    
    if period == "daily":
        filtered_df = sales_df[sales_df["date"] == max_date]
    elif period == "weekly":
        start_date = max_date - datetime.timedelta(days=7)
        filtered_df = sales_df[sales_df["date"] > start_date]
    elif period == "monthly":
        start_date = max_date - datetime.timedelta(days=30)
        filtered_df = sales_df[sales_df["date"] > start_date]
    else:
        filtered_df = sales_df
        
    # Group by product_id
    top_sales = filtered_df.groupby("product_id")["sales_qty"].sum().reset_index()
    top_sales = top_sales.merge(product_df, on="product_id", how="left")
    top_sales = top_sales.sort_values(by="sales_qty", ascending=False).head(10)
    
    return top_sales

def get_integrated_forecast(target_date_str, store_id, weather_label, temp, humidity, rainfall, is_rainy, engine):
    """
    Integrates ML models and Heuristics predictions. Calculates safety stock,
    safety-stock flags, recommended orders, and return values in a DataFrame.
    """
    engine.ensure_hourly_sales_loaded()
    # 1. Day information
    date_obj = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
    day_of_week = date_obj.weekday()
    
    # 2. Get predictions from both engines
    ml_preds = engine.predict_ml_demand(target_date_str, store_id, weather_label, temp, humidity, rainfall, is_rainy)
    store_row = engine.store_df[engine.store_df["store_id"] == store_id].iloc[0]
    rule_preds = calculate_rule_forecast(weather_label, store_row, day_of_week)
    
    # 3. Default typical weather baseline settings to compute relative scaling multiplier
    if weather_label == "비":
        def_temp, def_hum, def_rain = 16.0, 88.0, 14.5
    elif weather_label == "폭염":
        def_temp, def_hum, def_rain = 32.5, 62.0, 0.0
    else:  # "맑음"
        def_temp, def_hum, def_rain = 21.5, 52.0, 0.0
        
    # Get weekly popularity (only highlight the top 3 podium products as popular)
    weekly_top_df = get_top_products("weekly").head(3)
    weekly_top_ids = list(weekly_top_df["product_id"].unique()) if not weekly_top_df.empty else []
    
    integrated_results = []
    
    for p in BASELINE_PRODUCTS:
        p_id = p["id"]
        p_name = p["name"]
        category = p["category"]
        current_stock = p["current_stock"]
        shelf_life = p["shelf_life_type"]
        disposal_risk = p["disposal_risk"]
        price = p["price"]
        
        # Calculate the actual national average sales dynamically from all stores in the history
        sub_sales_all = engine.sales_df[engine.sales_df["product_id"] == p_id]
        if not sub_sales_all.empty:
            base_sales = round(float(sub_sales_all["sales_qty"].mean()), 1)
        else:
            base_sales = p["base_sales"]
        
        
        # Predictions
        ml_expected = ml_preds[p_id]
        rule_expected = rule_preds[p_id]["expected_sales"]
        reason = rule_preds[p_id]["reason"]
        
        # Get product master row
        prod_row = engine.product_df[engine.product_df["product_id"] == p_id].iloc[0]
        
        # Promotion analysis & multipliers
        promo_active = is_promotion_active(target_date_str, prod_row.get("promotion_start_date"), prod_row.get("promotion_end_date"))
        promo_multiplier = 1.0
        promo_reason = ""
        
        if promo_active:
            promo_type = str(prod_row.get("promotion_type"))
            if promo_type == "1+1":
                promo_multiplier = 1.4
                promo_reason = "🎁 1+1 행사 진행중 (+40% 수요 반영)"
            elif promo_type == "2+1":
                promo_multiplier = 1.2
                promo_reason = "🎁 2+1 행사 진행중 (+20% 수요 반영)"
            elif promo_type == "할인":
                rate = float(prod_row.get("discount_rate", 0.0))
                promo_multiplier = round(1.0 + rate * 1.5, 2)
                promo_reason = f"🏷️ 할인 행사 진행중 ({rate*100:.0f}% 할인, +{rate*150:.0f}% 수요 반영)"
                
        # Calculate continuous scaling multiplier based on slider state relative to base weather defaults
        current_factor = get_continuous_weather_factor(p_name, temp, humidity, rainfall)
        default_factor = get_continuous_weather_factor(p_name, def_temp, def_hum, def_rain)
        relative_mult = current_factor / default_factor
        
        # 시간·요일·공휴일·상권 패턴 보정
        temporal = compute_temporal_demand_features(
            engine.sales_df, store_id, p_id, target_date_str, engine.hourly_sales_df
        )
        temporal_mult, temporal_reason = get_trade_area_temporal_multiplier(
            store_row["trade_area_type"],
            p_name,
            day_of_week,
            temporal.get("peak_time_slot"),
            temporal.get("is_holiday", 0),
        )
        holiday_mult = get_holiday_demand_multiplier(temporal.get("is_holiday", 0))
        ma_ratio = 1.0
        if temporal["moving_average_28d"] > 0:
            ma_ratio = temporal["moving_average_7d"] / temporal["moving_average_28d"]
        ma_ratio = max(0.85, min(1.15, ma_ratio))

        expected_sales = round(
            float(ml_expected * relative_mult * promo_multiplier * temporal_mult * holiday_mult * ma_ratio), 1
        )
        
        # Safety Stock calculation
        safety_stock = get_dynamic_safety_stock(shelf_life, disposal_risk, expected_sales)
        
        # Final recommendation order: Expected Sales + Safety Stock - Current Stock (bounded at 0)
        recommended_order = int(max(0, round(expected_sales + safety_stock - current_stock)))
        
        # Alert thresholds: Stockout risk vs Disposal/Waste risk
        status = "정상"
        waste_risk = 0
        
        if current_stock < expected_sales:
            status = "품절 위험"
        elif shelf_life == "FF" and current_stock > (expected_sales * 1.5):
            status = "폐기 우려"
            waste_risk = int(max(0, current_stock - expected_sales))
            
        # Build recommendation reason
        reasons_list = []
        if promo_active:
            reasons_list.append(promo_reason)
        if p_id in weekly_top_ids:
            reasons_list.append("🔥 주간 인기상품")
            
        if temporal_reason:
            reasons_list.append(f"🕐 {temporal_reason}")
        reasons_list.append(
            f"시간·요일 반영(MA7={temporal['moving_average_7d']}, MA28={temporal['moving_average_28d']})"
        )

        if reasons_list:
            recommend_reason = " & ".join(reasons_list)
        else:
            recommend_reason = "기본 안정 수요 흐름 유지"
            
        integrated_results.append({
            "id": p_id,
            "name": p_name,
            "category": category,
            "price": price,
            "shelf_life_type": shelf_life,
            "disposal_risk": disposal_risk,
            "current_stock": current_stock,
            "safety_stock": safety_stock,
            "ml_expected": ml_expected,
            "rule_expected": rule_expected,
            "expected_sales": expected_sales,
            "recommended_order": recommended_order,
            "status": status,
            "waste_risk_qty": waste_risk,
            "reason": reason,
            "base_sales": base_sales,
            "original_price": float(prod_row.get("original_price", price)),
            "discount_price": float(prod_row.get("discount_price", price)),
            "discount_rate": float(prod_row.get("discount_rate", 0.0)),
            "promotion_type": str(prod_row.get("promotion_type", "None")),
            "is_1plus1": int(prod_row.get("is_1plus1", 0)),
            "is_2plus1": int(prod_row.get("is_2plus1", 0)),
            "promotion_start_date": str(prod_row.get("promotion_start_date", "None")),
            "promotion_end_date": str(prod_row.get("promotion_end_date", "None")),
            "recommend_reason": recommend_reason,
            "relative_mult": relative_mult,
            "promo_multiplier": promo_multiplier,
            "day_label": temporal.get("day_label", DAY_LABELS[day_of_week]),
            "is_weekend": temporal.get("is_weekend", 0),
            "is_holiday": temporal.get("is_holiday", 0),
            "hour": temporal.get("hour", 12),
            "previous_day_sales": temporal.get("previous_day_sales", 0),
            "previous_week_sales": temporal.get("previous_week_sales", 0),
            "moving_average_7d": temporal.get("moving_average_7d", 0),
            "moving_average_28d": temporal.get("moving_average_28d", 0),
            "recent_7d_avg": temporal.get("moving_average_7d", 0),
            "recent_4w_weekday_avg": temporal.get("recent_4w_weekday_avg", 0),
            "peak_time_slot": temporal.get("peak_time_slot", temporal.get("peak_period", "")),
            "peak_period": temporal.get("peak_period", "점심"),
            "demand_commute_morning": temporal.get("demand_commute_morning", 0),
            "demand_lunch": temporal.get("demand_lunch", 0),
            "demand_commute_evening": temporal.get("demand_commute_evening", 0),
            "demand_night": temporal.get("demand_night", 0),
            "temporal_reason": temporal.get("temporal_reason", ""),
            "temporal_mult": temporal_mult,
            "temporal_applied": True,
        })
        
    # Rainy condition safety guard: Cup Ramen weather multiplier can NEVER exceed Umbrella weather multiplier
    if rainfall > 0.0:
        umbrella_item = None
        ramen_item = None
        for item in integrated_results:
            if item["name"] == "우산":
                umbrella_item = item
            elif item["name"] == "컵라면":
                ramen_item = item
                
        if umbrella_item and ramen_item:
            umb_mult = umbrella_item["relative_mult"]
            ram_mult = ramen_item["relative_mult"]
            if ram_mult > umb_mult:
                # Force Ramen weather multiplier to be capped strictly at Umbrella's weather multiplier
                ramen_item["relative_mult"] = umb_mult
                # Recalculate Ramen's expected sales and recommended order based on capped multiplier
                new_sales = round(float(ramen_item["ml_expected"] * umb_mult * ramen_item["promo_multiplier"]), 1)
                ramen_item["expected_sales"] = new_sales
                
                # Re-calculate safety stock and recommended order with the capped sales
                new_safety = get_dynamic_safety_stock(ramen_item["shelf_life_type"], ramen_item["disposal_risk"], new_sales)
                ramen_item["safety_stock"] = new_safety
                ramen_item["recommended_order"] = int(max(0, round(new_sales + new_safety - ramen_item["current_stock"])))
                
                # Re-evaluate stock alert status
                if ramen_item["current_stock"] < new_sales:
                    ramen_item["status"] = "품절 위험"
                elif ramen_item["shelf_life_type"] == "FF" and ramen_item["current_stock"] > (new_sales * 1.5):
                    ramen_item["status"] = "폐기 우려"
                    ramen_item["waste_risk_qty"] = int(max(0, ramen_item["current_stock"] - new_sales))
                else:
                    ramen_item["status"] = "정상"
                    ramen_item["waste_risk_qty"] = 0
                    
    return pd.DataFrame(integrated_results)

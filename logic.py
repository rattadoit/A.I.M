import os
import random
import datetime
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from config import BASELINE_PRODUCTS

# Paths for CSV files
PRODUCT_CSV = "data/sample_product.csv"
STORE_CSV = "data/sample_store.csv"
WEATHER_CSV = "data/sample_weather.csv"
SALES_CSV = "data/sample_sales.csv"

class PredictionEngine:
    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.feature_cols = [
            "temp", "humidity", "rainy", "rainfall", 
            "day_of_week", "is_weekend",
            "cat_encoded", "dist_encoded", "prod_encoded",
            "recent_7d_avg", "recent_4w_weekday_avg"
        ]
        self.sales_df = None
        self.weather_df = None
        self.product_df = None
        self.store_df = None
        
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
        
        # Parse dates
        self.sales_df["date"] = pd.to_datetime(self.sales_df["date"])
        self.weather_df["date"] = pd.to_datetime(self.weather_df["date"])
        
    def engineer_features(self):
        """Engineers rolling historical averages and encoders for Random Forest training."""
        # 1. Merge all info
        df = self.sales_df.merge(self.store_df, on="store_id", how="left")
        df = df.merge(self.product_df, on="product_id", how="left")
        
        # Merge weather
        df = df.merge(self.weather_df, on="date", how="left")
        
        # Date parts
        df["day_of_week"] = df["date"].dt.weekday
        df["is_weekend"] = df["day_of_week"].apply(lambda x: 1 if x >= 5 else 0)
        
        # 2. Historical Feature Engineering (Shifted to prevent data leakage!)
        df = df.sort_values(by=["store_id", "product_id", "date"])
        
        # Recent 7d average
        df["recent_7d_avg"] = df.groupby(["store_id", "product_id"])["sales_qty"] \
                                .transform(lambda x: x.shift(1).rolling(7, min_periods=1).mean())
        
        # Recent 4w same day-of-week average
        df["recent_4w_weekday_avg"] = df.groupby(["store_id", "product_id", "day_of_week"])["sales_qty"] \
                                        .transform(lambda x: x.shift(1).rolling(4, min_periods=1).mean())
        
        # Fill NaN values (mostly the first few days of history)
        df["recent_7d_avg"] = df["recent_7d_avg"].fillna(df["sales_qty"].mean())
        df["recent_4w_weekday_avg"] = df["recent_4w_weekday_avg"].fillna(df["sales_qty"].mean())
        
        # 3. Label Encoding
        for col, new_col in [("category", "cat_encoded"), ("trade_area_type", "dist_encoded"), ("product_id", "prod_encoded")]:
            le = LabelEncoder()
            df[new_col] = le.fit_transform(df[col])
            self.label_encoders[col] = le
            
        return df

    def train_model(self):
        """Trains the Random Forest demand forecast model."""
        self.load_data()
        df = self.engineer_features()
        
        # Feature columns mapping
        X = df[[
            "temperature", "humidity", "rainy", "rainfall", 
            "day_of_week", "is_weekend",
            "cat_encoded", "dist_encoded", "prod_encoded",
            "recent_7d_avg", "recent_4w_weekday_avg"
        ]]
        y = df["sales_qty"]
        
        # Standard RF setup
        self.model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42)
        self.model.fit(X, y)
        print("Machine learning model training complete! Score:", round(self.model.score(X, y), 4))
        
    def predict_ml_demand(self, target_date_str, store_id, weather_label, temp, humidity, rainfall, is_rainy):
        """Predicts sales using the trained Random Forest regressor."""
        if self.model is None:
            self.train_model()
            
        date_obj = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
        day_of_week = date_obj.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0
        
        store_row = self.store_df[self.store_df["store_id"] == store_id].iloc[0]
        district = store_row["trade_area_type"]
        
        predictions = []
        
        for p in BASELINE_PRODUCTS:
            p_id = p["id"]
            category = p["category"]
            
            # Encode categories
            cat_enc = self.label_encoders["category"].transform([category])[0]
            dist_enc = self.label_encoders["trade_area_type"].transform([district])[0]
            prod_enc = self.label_encoders["product_id"].transform([p_id])[0]
            
            # Fetch rolling history for this store/product up to the latest date
            sub_sales = self.sales_df[(self.sales_df["store_id"] == store_id) & (self.sales_df["product_id"] == p_id)]
            
            if not sub_sales.empty:
                recent_7d = sub_sales.tail(7)["sales_qty"].mean()
                
                # Filter same weekday in history
                self.sales_df["day_of_week"] = pd.to_datetime(self.sales_df["date"]).dt.weekday
                weekday_sales = self.sales_df[(self.sales_df["store_id"] == store_id) & 
                                              (self.sales_df["product_id"] == p_id) & 
                                              (self.sales_df["day_of_week"] == day_of_week)]
                recent_4w = weekday_sales.tail(4)["sales_qty"].mean() if not weekday_sales.empty else recent_7d
            else:
                recent_7d = p["base_sales"]
                recent_4w = p["base_sales"]
                
            # Features block
            features = np.array([[
                temp, humidity, is_rainy, rainfall,
                day_of_week, is_weekend,
                cat_enc, dist_enc, prod_enc,
                recent_7d, recent_4w
            ]])
            
            pred_qty = round(float(self.model.predict(features)[0]), 1)
            predictions.append((p_id, pred_qty))
            
        return dict(predictions)

def calculate_rule_forecast(weather, district, day_of_week):
    """
    Computes baseline heuristic rule sales.
    Replicates the base sales heuristics from original code, adding weekend dampeners.
    """
    is_weekend = 1 if day_of_week >= 5 else 0
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
                w_mult = 1.8
                reasons.append("🍜 뜨거운 국물류 선호 (+80%)")
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
                d_mult = 2.0
                reasons.append("🏫 학생 간식 소비 폭발 (+100%)")
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
                
        expected_sales = round(p["base_sales"] * w_mult * d_mult * weekend_mult, 1)
        reason_str = " + ".join(reasons) if reasons else "기본 안정 수요 흐름 유지"
        
        forecast_results.append({
            "id": p["id"],
            "expected_sales": expected_sales,
            "reason": reason_str,
            "w_mult": w_mult,
            "d_mult": d_mult,
            "weekend_mult": weekend_mult
        })
        
    return {item["id"]: item for item in forecast_results}

def get_dynamic_safety_stock(shelf_life, disposal_risk, expected_sales):
    """
    Computes custom safety stock levels based on product shelf life and disposal risks.
    - HIGH risk (Fresh Foods): Tight safety margins to avoid heavy waste/write-offs.
    - MEDIUM risk: Moderate safety stocks.
    - LOW risk (Dry goods/Beverages): Higher safety stock to capture all sales and prevent stockouts.
    """
    if shelf_life == "FF":
        if disposal_risk == "HIGH":
            # Very tight safety margin (15% of expected sales)
            return max(1, int(round(expected_sales * 0.15)))
        else:
            # Medium disposal risk (30% of expected sales)
            return max(2, int(round(expected_sales * 0.30)))
    else:
        # Long shelf life, dry products (60% of expected sales)
        return max(3, int(round(expected_sales * 0.60)))

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
        # Extremely sensitive to rainfall.
        if rainfall > 0.0:
            factor = 1.0 + (rainfall * 0.9)  # +90% per 1mm rain (e.g. 10mm -> 10.0x)
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
        # Prefers rain and cold, dislikes heat
        temp_factor = 1.0 - (temp - 20.0) * 0.02  # -2% per 1C
        rain_bonus = 1.0 + (rainfall * 0.025)  # +2.5% per 1mm rain
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

def get_integrated_forecast(
    target_date_str,
    store_id,
    weather_label,
    temp,
    humidity,
    rainfall,
    is_rainy,
    engine,
    external_context=None,
):
    """
    Integrates ML models and Heuristics predictions. Calculates safety stock,
    safety-stock flags, recommended orders, and return values in a DataFrame.
    external_context: services.forecast_context.ExternalForecastContext (SNS·이벤트 uplift)
    """
    # 1. Day information
    date_obj = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
    day_of_week = date_obj.weekday()
    
    # 2. Get predictions from both engines
    ml_preds = engine.predict_ml_demand(target_date_str, store_id, weather_label, temp, humidity, rainfall, is_rainy)
    rule_preds = calculate_rule_forecast(weather_label, engine.store_df[engine.store_df["store_id"] == store_id].iloc[0]["trade_area_type"], day_of_week)
    
    # 3. Default typical weather baseline settings to compute relative scaling multiplier
    if weather_label == "비":
        def_temp, def_hum, def_rain = 16.0, 88.0, 14.5
    elif weather_label == "폭염":
        def_temp, def_hum, def_rain = 32.5, 62.0, 0.0
    else:  # "맑음"
        def_temp, def_hum, def_rain = 21.5, 52.0, 0.0
        
    integrated_results = []
    
    for p in BASELINE_PRODUCTS:
        p_id = p["id"]
        p_name = p["name"]
        category = p["category"]
        current_stock = p["current_stock"]
        shelf_life = p["shelf_life_type"]
        disposal_risk = p["disposal_risk"]
        price = p["price"]
        base_sales = p["base_sales"]
        
        # Predictions
        ml_expected = ml_preds[p_id]
        rule_expected = rule_preds[p_id]["expected_sales"]
        
        # Calculate continuous scaling multiplier based on slider state relative to base weather defaults
        current_factor = get_continuous_weather_factor(p_name, temp, humidity, rainfall)
        default_factor = get_continuous_weather_factor(p_name, def_temp, def_hum, def_rain)
        relative_mult = current_factor / default_factor
        
        # Blended expected sales (continuous gliding floats + external signals)
        base_expected = float(ml_expected * relative_mult)
        sns_u = 0.0
        evt_u = 0.0
        external_reason = ""
        if external_context is not None:
            sns_u = float(external_context.sns_by_product.get(p_id, 0.0))
            evt_u = float(external_context.event_by_product.get(p_id, 0.0))
            external_reason = external_context.reason_snippets.get(p_id, "")

        expected_sales = round(base_expected * (1.0 + sns_u) * (1.0 + evt_u), 1)

        reason = rule_preds[p_id]["reason"]
        if external_reason:
            reason = f"{reason} | {external_reason}"
        
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
            "base_expected": round(base_expected, 1),
            "sns_uplift": sns_u,
            "event_uplift": evt_u,
            "expected_sales": expected_sales,
            "recommended_order": recommended_order,
            "status": status,
            "waste_risk_qty": waste_risk,
            "reason": reason,
            "external_reason": external_reason,
            "base_sales": base_sales
        })
        
    return pd.DataFrame(integrated_results)

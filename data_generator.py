import os
import random
import datetime
import pandas as pd
import numpy as np

def calculate_location_multiplier(product_name, category, store):
    """Returns a prototype demand multiplier from sample location features."""
    school_count = store.get("school_count", 0)
    hospital_count = store.get("hospital_count", 0)
    office_count = store.get("office_count", 0)
    subway_distance = store.get("subway_distance", 800)
    commercial_density = store.get("commercial_density", 0.5)
    residential_ratio = store.get("residential_ratio", 0.5)

    multiplier = 1.0

    # Dense foot traffic lifts impulse-buy items across the board.
    multiplier += commercial_density * 0.08
    if subway_distance <= 250:
        multiplier += 0.08
    elif subway_distance <= 500:
        multiplier += 0.04

    if product_name in ["컵라면", "샌드위치", "아이스크림", "핫바"]:
        multiplier += min(school_count * 0.025, 0.18)

    if product_name in ["아메리카노", "도시락", "샌드위치"]:
        multiplier += min(office_count * 0.012, 0.22)

    if product_name in ["생수", "도시락", "아메리카노"]:
        multiplier += min(hospital_count * 0.018, 0.12)

    if product_name in ["맥주", "핫바", "도시락", "컵라면"]:
        multiplier += residential_ratio * 0.12

    if category == "음료":
        multiplier += commercial_density * 0.04

    return round(multiplier, 3)

def generate_synthesized_data():
    print("Generating simulated convenience store datasets...")
    
    # 1. Ensure output directory exists
    os.makedirs("data", exist_ok=True)
    
    # 2. Product Master Data (product_info)
    products = [
        {
            "product_id": "P01", "product_name": "도시락", "category": "식사", "shelf_life_type": "FF", "disposal_risk": "HIGH", "unit_price": 4800,
            "original_price": 4800, "discount_price": 4800, "discount_rate": 0.0, "promotion_type": "None", "is_1plus1": False, "is_2plus1": False,
            "promotion_start_date": "None", "promotion_end_date": "None"
        },
        {
            "product_id": "P02", "product_name": "아메리카노", "category": "음료", "shelf_life_type": "DRY", "disposal_risk": "LOW", "unit_price": 2000,
            "original_price": 2000, "discount_price": 2000, "discount_rate": 0.0, "promotion_type": "1+1", "is_1plus1": True, "is_2plus1": False,
            "promotion_start_date": "2026-05-01", "promotion_end_date": "2026-05-31"
        },
        {
            "product_id": "P03", "product_name": "우산", "category": "잡화", "shelf_life_type": "DRY", "disposal_risk": "LOW", "unit_price": 6000,
            "original_price": 6000, "discount_price": 6000, "discount_rate": 0.0, "promotion_type": "None", "is_1plus1": False, "is_2plus1": False,
            "promotion_start_date": "None", "promotion_end_date": "None"
        },
        {
            "product_id": "P04", "product_name": "생수", "category": "음료", "shelf_life_type": "DRY", "disposal_risk": "LOW", "unit_price": 1000,
            "original_price": 1000, "discount_price": 1000, "discount_rate": 0.0, "promotion_type": "None", "is_1plus1": False, "is_2plus1": False,
            "promotion_start_date": "None", "promotion_end_date": "None"
        },
        {
            "product_id": "P05", "product_name": "얼음컵", "category": "음료", "shelf_life_type": "FF", "disposal_risk": "MEDIUM", "unit_price": 800,
            "original_price": 800, "discount_price": 800, "discount_rate": 0.0, "promotion_type": "None", "is_1plus1": False, "is_2plus1": False,
            "promotion_start_date": "None", "promotion_end_date": "None"
        },
        {
            "product_id": "P06", "product_name": "컵라면", "category": "식사", "shelf_life_type": "DRY", "disposal_risk": "LOW", "unit_price": 1500,
            "original_price": 1500, "discount_price": 1500, "discount_rate": 0.0, "promotion_type": "2+1", "is_1plus1": False, "is_2plus1": True,
            "promotion_start_date": "2026-05-15", "promotion_end_date": "2026-05-25"
        },
        {
            "product_id": "P07", "product_name": "샌드위치", "category": "식사", "shelf_life_type": "FF", "disposal_risk": "HIGH", "unit_price": 2900,
            "original_price": 2900, "discount_price": 2300, "discount_rate": 0.21, "promotion_type": "할인", "is_1plus1": False, "is_2plus1": False,
            "promotion_start_date": "2026-05-20", "promotion_end_date": "2026-05-30"
        },
        {
            "product_id": "P08", "product_name": "맥주", "category": "주류", "shelf_life_type": "DRY", "disposal_risk": "LOW", "unit_price": 3500,
            "original_price": 3500, "discount_price": 3500, "discount_rate": 0.0, "promotion_type": "None", "is_1plus1": False, "is_2plus1": False,
            "promotion_start_date": "None", "promotion_end_date": "None"
        },
        {
            "product_id": "P09", "product_name": "아이스크림", "category": "간식", "shelf_life_type": "FF", "disposal_risk": "MEDIUM", "unit_price": 1200,
            "original_price": 1200, "discount_price": 1200, "discount_rate": 0.0, "promotion_type": "1+1", "is_1plus1": True, "is_2plus1": False,
            "promotion_start_date": "2026-05-01", "promotion_end_date": "2026-05-31"
        },
        {
            "product_id": "P10", "product_name": "핫바", "category": "간식", "shelf_life_type": "FF", "disposal_risk": "MEDIUM", "unit_price": 2200,
            "original_price": 2200, "discount_price": 2200, "discount_rate": 0.0, "promotion_type": "None", "is_1plus1": False, "is_2plus1": False,
            "promotion_start_date": "None", "promotion_end_date": "None"
        },
    ]
    pd.DataFrame(products).to_csv("data/sample_product.csv", index=False, encoding="utf-8-sig")
    
    # 3. Store Master Data (store_info)
    stores = [
        {
            "store_id": "S001",
            "store_name": "대학가 학생점",
            "trade_area_type": "학교",
            "region": "서울",
            "latitude": 37.5584,
            "longitude": 126.9459,
            "address": "서울시 서대문구 대학가 인근",
            "school_count": 6,
            "hospital_count": 1,
            "office_count": 5,
            "subway_distance": 280,
            "commercial_density": 0.72,
            "residential_ratio": 0.38,
            "store_area_type": "대학가",
        },
        {
            "store_id": "S002",
            "store_name": "여의도 금융가점",
            "trade_area_type": "오피스",
            "region": "서울",
            "latitude": 37.5259,
            "longitude": 126.9245,
            "address": "서울시 영등포구 여의도 업무지구",
            "school_count": 1,
            "hospital_count": 2,
            "office_count": 22,
            "subway_distance": 180,
            "commercial_density": 0.91,
            "residential_ratio": 0.18,
            "store_area_type": "오피스밀집",
        },
        {
            "store_id": "S003",
            "store_name": "마포래미안 주거점",
            "trade_area_type": "주거지",
            "region": "서울",
            "latitude": 37.5519,
            "longitude": 126.9134,
            "address": "서울시 마포구 대단지 아파트 인근",
            "school_count": 3,
            "hospital_count": 3,
            "office_count": 4,
            "subway_distance": 620,
            "commercial_density": 0.56,
            "residential_ratio": 0.82,
            "store_area_type": "주거밀집",
        },
    ]
    pd.DataFrame(stores).to_csv("data/sample_store.csv", index=False, encoding="utf-8-sig")
    
    # 4. Generate 60 days of Daily Weather (weather_daily)
    # Target period: 60 days leading up to today (2026-05-22). Let's start from 2026-03-23 to 2026-05-21.
    start_date = datetime.date(2026, 3, 23)
    num_days = 60
    
    weather_list = []
    
    # Base multipliers from prompt guidelines:
    # 우산: 비 10.0x
    # 컵라면: 비 1.8x, 폭염 0.6x, 학교 2.0x
    # 도시락: 비 1.2x, 오피스 1.6x, 주거지 1.2x
    # 아이스크림: 비 0.5x, 폭염 2.0x, 맑음 1.5x, 학교 1.5x
    # 얼음컵: 폭염 3.5x
    # 생수: 폭염 3.0x
    # 아메리카노: 폭염 2.5x, 오피스 2.5x
    # 맥주: 맑음 1.2x, 주거지 2.0x
    # 샌드위치: 학교 1.8x, 오피스 1.5x
    # 핫바: 주거지 1.5x
    
    random.seed(42)
    np.random.seed(42)
    
    for i in range(num_days):
        current_date = start_date + datetime.timedelta(days=i)
        
        # Simulating seasonal temperature warming from March (avg 11C) to May (avg 24C)
        base_temp = 11.0 + (13.0 * (i / num_days)) + np.random.normal(0, 2.0)
        
        # Decide weather condition
        rain_prob = 0.18
        is_rainy = 1 if random.random() < rain_prob else 0
        
        if is_rainy:
            rainfall = round(random.uniform(2.0, 35.0), 1)
            temperature = base_temp - random.uniform(1.5, 4.0)  # rain drops temperature
            humidity = round(random.uniform(75.0, 98.0), 1)
        else:
            rainfall = 0.0
            temperature = base_temp
            humidity = round(random.uniform(40.0, 68.0), 1)
            
        feels_like = temperature + (0.1 * (humidity - 50.0)) if temperature > 20 else temperature
        
        weather_list.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "region": "서울",
            "temperature": round(temperature, 1),
            "feels_like": round(feels_like, 1),
            "rainfall": rainfall,
            "rainy": is_rainy,
            "humidity": round(humidity, 1)
        })
        
    weather_df = pd.DataFrame(weather_list)
    weather_df.to_csv("data/sample_weather.csv", index=False, encoding="utf-8-sig")
    
    # 5. Generate Sales History (sales_history)
    # product specific baseline sales parameters
    prod_baselines = {
        "P01": {"base_sales": 15, "name": "도시락"},
        "P02": {"base_sales": 30, "name": "아메리카노"},
        "P03": {"base_sales": 2,  "name": "우산"},
        "P04": {"base_sales": 25, "name": "생수"},
        "P05": {"base_sales": 40, "name": "얼음컵"},
        "P06": {"base_sales": 20, "name": "컵라면"},
        "P07": {"base_sales": 12, "name": "샌드위치"},
        "P08": {"base_sales": 18, "name": "맥주"},
        "P09": {"base_sales": 15, "name": "아이스크림"},
        "P10": {"base_sales": 10, "name": "핫바"}
    }
    
    sales_history = []
    
    for row in weather_list:
        date_str = row["date"]
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        day_of_week = date_obj.weekday()  # 0: Mon, ..., 6: Sun
        is_weekend = 1 if day_of_week >= 5 else 0
        
        # Extract weather status label for rule calculations
        temp = row["temperature"]
        is_rain = row["rainy"]
        
        if is_rain:
            weather_status = "비"
        elif temp >= 26.5:
            weather_status = "폭염"
        else:
            weather_status = "맑음"
            
        for store in stores:
            s_id = store["store_id"]
            district = store["trade_area_type"]
            
            for prod in products:
                p_id = prod["product_id"]
                p_name = prod["product_name"]
                category = prod["category"]
                shelf_life = prod["shelf_life_type"]
                
                # Retrieve base sales
                base = prod_baselines[p_id]["base_sales"]
                
                # Rule-based multipliers (replicated in logic.py)
                w_mult = 1.0
                if weather_status == "비":
                    if p_name == "우산": w_mult = 10.0
                    elif p_name == "컵라면": w_mult = 1.8
                    elif p_name == "도시락": w_mult = 1.2
                    elif p_name == "아이스크림": w_mult = 0.5
                elif weather_status == "폭염":
                    if p_name == "얼음컵": w_mult = 3.5
                    elif p_name == "생수": w_mult = 3.0
                    elif p_name == "아메리카노": w_mult = 2.5
                    elif p_name == "아이스크림": w_mult = 2.0
                    elif p_name == "컵라면": w_mult = 0.6
                elif weather_status == "맑음":
                    if p_name == "아이스크림": w_mult = 1.5
                    elif p_name == "맥주": w_mult = 1.2
                    
                d_mult = 1.0
                if district == "학교":
                    if p_name == "컵라면": d_mult = 2.0
                    elif p_name == "샌드위치": d_mult = 1.8
                    elif p_name == "아이스크림": d_mult = 1.5
                elif district == "오피스":
                    if p_name == "아메리카노": d_mult = 2.5
                    elif p_name == "도시락": d_mult = 1.6
                    elif p_name == "샌드위치": d_mult = 1.5
                elif district == "주거지":
                    if p_name == "맥주": d_mult = 2.0
                    elif p_name == "핫바": d_mult = 1.5
                    elif p_name == "도시락": d_mult = 1.2
                    
                # Weekend effect multipliers
                # Office sales drop significantly on weekend
                # School sales drop completely on weekend
                # Residential sales stay normal or slightly increase for beer/snacks
                weekend_mult = 1.0
                if is_weekend:
                    if district == "오피스":
                        weekend_mult = 0.25 if category in ["식사", "음료"] else 0.4
                    elif district == "학교":
                        weekend_mult = 0.15 if category in ["식사", "음료"] else 0.3
                    elif district == "주거지":
                        if p_name == "맥주": weekend_mult = 1.6
                        elif p_name == "핫바": weekend_mult = 1.3
                        else: weekend_mult = 1.1
                else:
                    # Weekday increases office/school demand slightly
                    if district in ["오피스", "학교"]:
                        weekend_mult = 1.2
                
                # Compute base expected sales
                location_mult = calculate_location_multiplier(p_name, category, store)
                expected = base * w_mult * d_mult * weekend_mult * location_mult
                
                # Add Gaussian noise
                noise = np.random.normal(0, max(1.5, expected * 0.12))
                true_demand = max(0.0, expected + noise)
                
                # stock allocation logic for generating historical sales qty
                # We assume stores generally order based on recent sales, meaning stock levels fluctuate around expected demand
                stock = int(max(expected * random.uniform(0.9, 1.4) + random.randint(1, 5), 1))
                
                # Actual Sales is capped at available stock
                sales = int(min(stock, round(true_demand)))
                
                # Sold out condition
                sold_out = 0
                sold_out_time = ""
                if sales >= stock:
                    sold_out = 1
                    # Random hour for sold out simulation
                    sold_out_time = f"{random.randint(14, 21)}:{random.choice([0, 15, 30, 45]):02d}"
                
                # Waste calculation for Fresh Food (FF) items
                leftover = stock - sales
                disposed = 0
                if shelf_life == "FF" and leftover > 0:
                    # high risk wastes more, medium risk wastes moderately
                    waste_pct = 0.65 if prod["disposal_risk"] == "HIGH" else 0.35
                    disposed = int(round(leftover * waste_pct * random.uniform(0.8, 1.2)))
                    disposed = min(leftover, disposed)
                
                sales_history.append({
                    "date": date_str,
                    "store_id": s_id,
                    "product_id": p_id,
                    "sales_qty": sales,
                    "stock_qty": stock,
                    "disposed_qty": disposed,
                    "sold_out": sold_out,
                    "sold_out_time": sold_out_time if sold_out == 1 else "",
                    "original_price": prod["original_price"],
                    "discount_price": prod["discount_price"],
                    "discount_rate": prod["discount_rate"],
                    "promotion_type": prod["promotion_type"],
                    "is_1plus1": prod["is_1plus1"],
                    "is_2plus1": prod["is_2plus1"],
                    "promotion_start_date": prod["promotion_start_date"],
                    "promotion_end_date": prod["promotion_end_date"]
                })
                
    sales_df = pd.DataFrame(sales_history)
    sales_df.to_csv("data/sample_sales.csv", index=False, encoding="utf-8-sig")
    print(f"Data generation complete! Saved files to 'data/' folder. Total sales records: {len(sales_df)}")

if __name__ == "__main__":
    generate_synthesized_data()

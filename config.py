PAGE_CONFIG = {
    "page_title": "AI Smart Order - 편의점 수요 예측 및 발주 자동화 시스템",
    "page_icon": "🏪",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

WEATHER_OPTIONS = ["맑음", "비", "폭염"]
DISTRICT_OPTIONS = ["학교", "오피스", "주거지"]

# baseline products enriched with ML schema metadata
# 상품 상세 정보 저장
BASELINE_PRODUCTS = [
    {
        "id": "P01", 
        "name": "도시락", 
        "category": "식사", 
        "base_sales": 15, 
        "current_stock": 8, 
        "safety_stock": 10, 
        "price": 4800, 
        "shelf_life_type": "FF", 
        "disposal_risk": "HIGH"
    },
    {
        "id": "P02", 
        "name": "아메리카노", 
        "category": "음료", 
        "base_sales": 30, 
        "current_stock": 12, 
        "safety_stock": 15, 
        "price": 2000, 
        "shelf_life_type": "DRY", 
        "disposal_risk": "LOW"
    },
    {
        "id": "P03", 
        "name": "우산", 
        "category": "잡화", 
        "base_sales": 2, 
        "current_stock": 3, 
        "safety_stock": 5, 
        "price": 6000, 
        "shelf_life_type": "DRY", 
        "disposal_risk": "LOW"
    },
    {
        "id": "P04", 
        "name": "생수", 
        "category": "음료", 
        "base_sales": 25, 
        "current_stock": 10, 
        "safety_stock": 12, 
        "price": 1000, 
        "shelf_life_type": "DRY", 
        "disposal_risk": "LOW"
    },
    {
        "id": "P05", 
        "name": "얼음컵", 
        "category": "음료", 
        "base_sales": 40, 
        "current_stock": 18, 
        "safety_stock": 20, 
        "price": 800, 
        "shelf_life_type": "FF", 
        "disposal_risk": "MEDIUM"
    },
    {
        "id": "P06", 
        "name": "컵라면", 
        "category": "식사", 
        "base_sales": 20, 
        "current_stock": 22, 
        "safety_stock": 10, 
        "price": 1500, 
        "shelf_life_type": "DRY", 
        "disposal_risk": "LOW"
    },
    {
        "id": "P07", 
        "name": "샌드위치", 
        "category": "식사", 
        "base_sales": 12, 
        "current_stock": 5, 
        "safety_stock": 8, 
        "price": 2900, 
        "shelf_life_type": "FF", 
        "disposal_risk": "HIGH"
    },
    {
        "id": "P08", 
        "name": "맥주", 
        "category": "주류", 
        "base_sales": 18, 
        "current_stock": 25, 
        "safety_stock": 12, 
        "price": 3500, 
        "shelf_life_type": "DRY", 
        "disposal_risk": "LOW"
    },
    {
        "id": "P09", 
        "name": "아이스크림", 
        "category": "간식", 
        "base_sales": 15, 
        "current_stock": 6, 
        "safety_stock": 10, 
        "price": 1200, 
        "shelf_life_type": "FF", 
        "disposal_risk": "MEDIUM"
    },
    {
        "id": "P10", 
        "name": "핫바", 
        "category": "간식", 
        "base_sales": 10, 
        "current_stock": 4, 
        "safety_stock": 6, 
        "price": 2200, 
        "shelf_life_type": "FF", 
        "disposal_risk": "MEDIUM"
    },
]

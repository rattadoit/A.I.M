import streamlit as st
import pandas as pd
import os
from config import PAGE_CONFIG
from styles import load_custom_css
from logic import PredictionEngine, get_integrated_forecast
from ui import (
    render_sidebar,
    render_header,
    render_kpi,
    render_product_table,
    render_chart,
    render_reasoning,
    render_executive_report,
    render_feedback_analysis_tab,
    render_footer,
    init_order_session_state,
    render_top_products_view,
)

# 1. Streamlit Caching for Prediction Engine (prevents retraining on every widget slide!)
@st.cache_resource
def load_and_train_prediction_engine():
    engine = PredictionEngine()
    engine.train_model()
    return engine

def main():
    # 2. Page Configuration
    st.set_page_config(**PAGE_CONFIG)
    
    # 3. Inject Glassmorphic CSS Styling
    load_custom_css()

    # 발주 이상치 팝업 session_state 선초기화
    init_order_session_state()
    
    # 4. Initialize ML Engine
    try:
        engine = load_and_train_prediction_engine()
    except Exception as e:
        st.error(f"🚨 머신러닝 엔진 초기화 및 학습에 실패했습니다: {e}")
        st.info("데이터 파일이 올바르게 생성되었는지 확인해 주세요.")
        return
        
    # 5. Sidebar Simulation Controller
    store_id, weather, temp, humidity, rainfall, is_rainy, date_str = render_sidebar(engine.store_df)
    
    # Extract store attributes for header
    store_row = engine.store_df[engine.store_df["store_id"] == store_id].iloc[0]
    store_name = store_row["store_name"]
    district = store_row["trade_area_type"]
    store_area_type = store_row.get("store_area_type", district)
    
    # 6. Execute Dual Prediction Core
    forecast_df = get_integrated_forecast(
        target_date_str=date_str,
        store_id=store_id,
        weather_label=weather,
        temp=temp,
        humidity=humidity,
        rainfall=rainfall,
        is_rainy=is_rainy,
        engine=engine
    )
    
    # 7. Navigation Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏪 실시간 스마트 발주 추천", 
        "🔥 인기 상품 트렌드 분석",
        "📊 피드백 분석 & SQLite 이력", 
        "🔍 데이터 스키마 & 원본 CSV 탐색"
    ])
    
    with tab1:
        # Header Rendering
        render_header(date_str, store_name, weather, district, temp, store_area_type)
        
        # Metric Rows
        render_kpi(forecast_df)
        
        st.write("") # Spacer
        
        # 1. Detailed prediction table spanning full page width for wide layout
        render_product_table(forecast_df, date_str, store_id)
        
        st.write("") # Spacer between Table and bottom section
        
        # 2. Dual-column split for report, chart, and heuristics log
        col_left, col_right = st.columns([5, 4])
        
        with col_left:
            # Dynamic Heuristic & ML summary text generator
            render_executive_report(forecast_df, weather, store_name, district, temp, rainfall)
            
            st.write("") # Spacer below report
            
            # Real-time Weather/District feature reaction horizontal bar chart
            render_chart(forecast_df)
            
        with col_right:
            # Decision heuristics detail log
            render_reasoning(forecast_df)
        
    with tab2:
        # Render real-time Popularity trends
        render_top_products_view()
        
    with tab3:
        # Render database log metrics and correlation scatterplots
        render_feedback_analysis_tab()
        
    with tab4:
        st.markdown('<div class="sec-title">🔍 시스템 원본 데이터 및 스키마 탐색기</div>', unsafe_allow_html=True)
        
        st.write("본 대시보드는 합성 생성기(`data_generator.py`)가 만든 과거 60일치 판매 내역과 날씨 데이터를 로드하여 구동됩니다. 아래 서브 탭을 통해 원본 데이터를 확인할 수 있습니다.")
        
        sub_t1, sub_t2, sub_t3, sub_t4, sub_t5 = st.tabs([
            "📋 상품 마스터 (product.csv)", 
            "🏪 점포 마스터 (store.csv)", 
            "⛅ 일자별 날씨 관측 (weather.csv)", 
            "📈 과거 판매 실적 (sales.csv)",
            "📄 데이터베이스 스키마 규격"
        ])
        
        with sub_t1:
            st.dataframe(engine.product_df, use_container_width=True, hide_index=True)
        with sub_t2:
            st.dataframe(engine.store_df, use_container_width=True, hide_index=True)
        with sub_t3:
            st.dataframe(engine.weather_df, use_container_width=True, hide_index=True)
        with sub_t4:
            st.dataframe(engine.sales_df.head(100), use_container_width=True, hide_index=True)
            st.caption("과거 60일치 전체 1,800건의 레코드 중 상위 100건을 표시 중입니다.")
        with sub_t5:
            # Load and display data_schema.md if available
            schema_path = "data/data_schema.md"
            if os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as f:
                    st.markdown(f.read())
            else:
                st.caption("스키마 명세서 파일이 없습니다.")
                
    # 8. Render Cosmic Footer
    render_footer()

if __name__ == "__main__":
    main()

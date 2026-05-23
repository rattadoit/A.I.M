import streamlit as st
import pandas as pd
import os
from config import PAGE_CONFIG, SETTINGS
from styles import load_custom_css
from logic import PredictionEngine
from services.forecast_service import build_forecast
from services.signal_service import load_external_signals
from services.demand_adjuster import build_external_context
from ui import (
    render_sidebar,
    render_header,
    render_kpi,
    render_product_table,
    render_chart,
    render_reasoning,
    render_executive_report,
    render_feedback_analysis_tab,
    render_external_signals_panel,
    render_backtest_tab,
    render_footer
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
    region = store_row["region"] if "region" in store_row.index else "서울"

    # 6. External signals (SNS + Events) — cached
    trends, events, signal_status = load_external_signals(
        store_id, date_str, district, region
    )
    ext_ctx = build_external_context(trends, events)

    # 7. Integrated forecast with external uplifts
    forecast_df = build_forecast(
        target_date_str=date_str,
        store_id=store_id,
        weather_label=weather,
        temp=temp,
        humidity=humidity,
        rainfall=rainfall,
        is_rainy=is_rainy,
        engine=engine,
        trends=trends,
        events=events,
    )
    
    # 8. Navigation Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏪 실시간 스마트 발주 추천",
        "📡 SNS·이벤트 신호",
        "📊 피드백 분석 & SQLite 이력",
        "🔍 데이터·백테스트",
    ])
    
    with tab1:
        render_header(date_str, store_name, weather, district, temp)
        if SETTINGS.USE_MOCK_EXTERNAL:
            st.caption(f"외부 신호: {signal_status} (Mock 모드)")
        else:
            st.caption(f"외부 신호: {signal_status}")

        render_kpi(forecast_df)
        st.write("")

        col_left, col_right = st.columns([5, 4])
        with col_left:
            render_product_table(forecast_df, date_str, store_id)
        with col_right:
            render_chart(forecast_df)
            render_reasoning(forecast_df)
        st.write("")
        render_executive_report(
            forecast_df, weather, store_name, district, temp,
            trend_summaries=ext_ctx.trend_summaries,
            event_summaries=ext_ctx.event_summaries,
        )
        
    with tab2:
        render_external_signals_panel(trends, events, signal_status)
        
    with tab3:
        render_feedback_analysis_tab()
        
    with tab4:
        st.markdown('<div class="sec-title">🔍 시스템 원본 데이터 및 스키마 탐색기</div>', unsafe_allow_html=True)
        sub_data, sub_bt = st.tabs(["📂 원본 CSV·스키마", "📉 백테스트"])
        with sub_data:
            st.write("합성 생성기(`data_generator.py`) 기반 60일 판매·날씨 데이터입니다.")
            sub_t1, sub_t2, sub_t3, sub_t4, sub_t5 = st.tabs([
                "📋 상품", "🏪 점포", "⛅ 날씨", "📈 판매", "📄 스키마",
            ])
            with sub_t1:
                st.dataframe(engine.product_df, use_container_width=True, hide_index=True)
            with sub_t2:
                st.dataframe(engine.store_df, use_container_width=True, hide_index=True)
            with sub_t3:
                st.dataframe(engine.weather_df, use_container_width=True, hide_index=True)
            with sub_t4:
                st.dataframe(engine.sales_df.head(100), use_container_width=True, hide_index=True)
            with sub_t5:
                schema_path = "data/data_schema.md"
                if os.path.exists(schema_path):
                    with open(schema_path, "r", encoding="utf-8") as f:
                        st.markdown(f.read())
        with sub_bt:
            render_backtest_tab(engine, store_id)
                
    render_footer()

if __name__ == "__main__":
    main()

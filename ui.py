import streamlit as st
import datetime
import pandas as pd
import plotly.graph_objects as go
from config import WEATHER_OPTIONS, DISTRICT_OPTIONS
from database import save_recommendation_feedback, get_feedback_history, get_feedback_metrics

def render_html(html_str):
    cleaned = "".join([line.strip() for line in html_str.split("\n")])
    st.markdown(cleaned, unsafe_allow_html=True)

def render_sidebar(store_df):
    with st.sidebar:
        st.markdown('<div style="text-align: center; padding: 10px 0;"><h3 style="font-family: \'Outfit\', sans-serif; color: #0f172a; margin-bottom: 5px;">🏪 AI Smart Order</h3><p style="color: #6d28d9; font-size: 0.82rem; font-weight: 600;">데이터 기반 수요예측 & 자동 발주</p></div>', unsafe_allow_html=True)
        st.markdown("---")
        
        st.subheader("⚙️ 상권 및 점포 설정")
        
        # Store selection
        store_options = {row["store_id"]: f"{row['store_name']} ({row['trade_area_type']})" for _, row in store_df.iterrows()}
        selected_store_id = st.selectbox(
            "📍 대상 점포 선택",
            options=list(store_options.keys()),
            format_func=lambda x: store_options[x]
        )
        
        selected_store_row = store_df[store_df["store_id"] == selected_store_id].iloc[0]
        district = selected_store_row["trade_area_type"]
        
        st.markdown("---")
        st.subheader("⛅ 외부 환경 시뮬레이터")
        
        # Weather Dropdown
        weather = st.selectbox(
            "오늘의 기상 상태",
            options=WEATHER_OPTIONS,
            index=0,
            help="기상 구분에 따라 기온/강수량 등의 기본값이 정해지며, 개별 슬라이더로 추가 미세조정이 가능합니다."
        )
        
        # Sets initial sliding scale parameters based on weather selection
        if weather == "맑음":
            init_temp = 21.5
            init_humidity = 52.0
            init_rainfall = 0.0
            init_rainy = 0
        elif weather == "비":
            init_temp = 16.0
            init_humidity = 88.0
            init_rainfall = 14.5
            init_rainy = 1
        elif weather == "폭염":
            init_temp = 32.5
            init_humidity = 62.0
            init_rainfall = 0.0
            init_rainy = 0
            
        temp = st.slider("🌡️ 외부 온도 (℃)", min_value=0.0, max_value=40.0, value=init_temp, step=0.5)
        humidity = st.slider("💧 대기 습도 (%)", min_value=10.0, max_value=100.0, value=init_humidity, step=1.0)
        rainfall = st.slider("🌧️ 강수량 (mm)", min_value=0.0, max_value=80.0, value=init_rainfall, step=0.5)
        
        is_rainy = 1 if rainfall > 0 else 0
        
        st.markdown("---")
        st.subheader("📅 분석 기준일")
        target_date = st.date_input("발주 분석일", value=datetime.date(2026, 5, 22))
        
        st.markdown('<div style="margin-top: 50px; text-align: center; color: #475569; font-size: 0.72rem; font-weight: 500;">Convenience Demand AI Engine v2.0<br>© Antigravity Advanced Analytics</div>', unsafe_allow_html=True)
        
    return selected_store_id, weather, temp, humidity, rainfall, is_rainy, target_date.strftime("%Y-%m-%d")

def render_header(date_str, store_name, weather, district, temp):
    render_html(f"""
    <div class="header-container">
        <span class="badge-ai">AI SMART ORDER MVP</span>
        <h1 class="main-title">🏪 {store_name} 스마트 발주 추천</h1>
        <p class="subtitle">분석일자: <b>{date_str}</b> | 날씨: <b>{weather} ({temp}℃)</b> | 상권 특성: <b>{district}</b></p>
    </div>
    """)

def render_kpi(forecast_df):
    danger_items = forecast_df[forecast_df["status"] == "품절 위험"]
    waste_items = forecast_df[forecast_df["status"] == "폐기 우려"]
    total_predicted_sales = forecast_df["expected_sales"].sum()
    total_recommended_orders = forecast_df["recommended_order"].sum()
    danger_count = len(danger_items)
    waste_count = len(waste_items)
    
    kpi_cols = st.columns(4)
    
    with kpi_cols[0]:
        render_html(f"""
        <div class="glass-card" style="margin-bottom: 0px; padding: 20px;">
            <div class="metric-hdr">✨ 예상 판매 수량</div>
            <div class="metric-num">{total_predicted_sales:.1f}<span class="unit">개</span></div>
            <div class="metric-subtext">오늘 전체 상품의 AI 예측 수요 총합</div>
        </div>
        """)
    
    with kpi_cols[1]:
        render_html(f"""
        <div class="glass-card" style="margin-bottom: 0px; padding: 20px;">
            <div class="metric-hdr" style="color: #6d28d9;">💜 추천 발주 총량</div>
            <div class="metric-num" style="color: #6d28d9;">{total_recommended_orders}<span class="unit" style="color: #6d28d9;">개</span></div>
            <div class="metric-subtext">예측수요 및 안전재고 보정 대비 필요 수량</div>
        </div>
        """)
    
    with kpi_cols[2]:
        sub_txt = "재고가 예측치보다 부족합니다." if danger_count > 0 else "재고 보유량이 모든 상품에 충분합니다."
        cls = "danger" if danger_count > 0 else ""
        render_html(f"""
        <div class="glass-card" style="margin-bottom: 0px; padding: 20px;">
            <div class="metric-hdr {cls}">⚠️ 품절 위험 상품</div>
            <div class="metric-num {cls}">{danger_count}<span class="unit {cls}">품목</span></div>
            <div class="metric-subtext">{sub_txt}</div>
        </div>
        """)
        
    with kpi_cols[3]:
        sub_txt = "유통기한 임박 폐기 가능성이 큽니다." if waste_count > 0 else "보유 재고량이 적정선 이하입니다."
        cls = "warning" if waste_count > 0 else ""
        text_color = "style='color: #b45309;'" if waste_count > 0 else ""
        render_html(f"""
        <div class="glass-card" style="margin-bottom: 0px; padding: 20px;">
            <div class="metric-hdr" {text_color}>📉 폐기 위험 상품</div>
            <div class="metric-num" {text_color}>{waste_count}<span class="unit" {text_color}>품목</span></div>
            <div class="metric-subtext">{sub_txt}</div>
        </div>
        """)

def render_product_table(forecast_df, date_str, store_id):
    st.markdown('<div class="sec-title">📋 상품별 예측 상세 정보 및 발주 수량 조정</div>', unsafe_allow_html=True)
    
    # 1. Prepare display DataFrame for Streamlit Editor
    display_df = forecast_df.copy()
    
    # Populate the initial owner adjusted column as recommended orders
    if "adjusted_order" not in st.session_state:
        st.session_state.adjusted_order = {row["id"]: int(row["recommended_order"]) for _, row in display_df.iterrows()}
        
    display_df["adjusted_order"] = display_df["id"].map(st.session_state.adjusted_order)
    
    # Format columns for nice reading
    display_df_viewer = display_df[[
        "id", "category", "name", "current_stock", "safety_stock", 
        "ml_expected", "rule_expected", "recommended_order", "adjusted_order", "status"
    ]]
    
    # Customize column metadata
    edited_df = st.data_editor(
        display_df_viewer,
        column_config={
            "id": st.column_config.TextColumn("코드", disabled=True),
            "category": st.column_config.TextColumn("카테고리", disabled=True),
            "name": st.column_config.TextColumn("상품명", disabled=True),
            "current_stock": st.column_config.NumberColumn("현재 재고 (개)", disabled=True),
            "safety_stock": st.column_config.NumberColumn("안전 재고 (개)", disabled=True),
            "ml_expected": st.column_config.NumberColumn("ML 예측 (개)", disabled=True),
            "rule_expected": st.column_config.NumberColumn("규칙 예측 (개)", disabled=True),
            "recommended_order": st.column_config.NumberColumn("AI 추천 발주", disabled=True),
            "adjusted_order": st.column_config.NumberColumn(
                "✍️ 점주 수동 조정 (개)", 
                min_value=0, 
                max_value=150, 
                step=1,
                help="발주할 최종 수량을 직접 수정할 수 있습니다."
            ),
            "status": st.column_config.TextColumn("진단 상태", disabled=True)
        },
        use_container_width=True,
        hide_index=True,
        key="data_editor_grid"
    )
    
    # Sync edits back to session state to prevent state loss
    for _, row in edited_df.iterrows():
        p_id = row["id"]
        val = int(row["adjusted_order"])
        st.session_state.adjusted_order[p_id] = val
        
    st.write("")
    
    # Propose SQLite submit button
    submit_col1, submit_col2 = st.columns([3, 7])
    
    with submit_col1:
        if st.button("🔥 최종 발주 수량 확정 및 피드백 전송", use_container_width=True, type="primary"):
            # Write adjustments to SQLite
            for _, row in display_df.iterrows():
                p_id = row["id"]
                p_name = row["name"]
                
                predicted_sales = float(row["expected_sales"])
                safety_stock = int(row["safety_stock"])
                current_stock = int(row["current_stock"])
                rec_order = int(row["recommended_order"])
                adj_order = int(st.session_state.adjusted_order[p_id])
                
                save_recommendation_feedback(
                    date_str=date_str,
                    store_id=store_id,
                    product_id=p_id,
                    predicted_sales=predicted_sales,
                    safety_stock=safety_stock,
                    current_stock=current_stock,
                    recommended_order=rec_order,
                    adjusted_order=adj_order
                )
                
            st.success("✅ 최종 발주가 성공적으로 접수되었습니다. (SQLite DB 기록 및 피드백 누적 완료)")
            
            with st.expander("🤖 AI 모델 피드백 반영 시뮬레이션 로그", expanded=True):
                st.code(f"""
[12:00:00] [Feedback Loop] 점주 수동 수정 이력 저장 완료: {date_str} / Store: {store_id}
[12:00:01] [Feedback Loop] AI 추천 대비 점주 수정 변동 항목 분석 완료.
[12:00:02] [Feedback Loop] 실제 판매량 추적이 이루어진 후, 본 수정 오차(Deviation)를 가중치 손실 함수(Loss Function)로 피딩합니다.
[12:00:03] [Feedback Loop] {store_id} 점포의 예측 편향성(Bias) 보정이 다음 모델 학습 사이클에 예약되었습니다.
                """)
                
    with submit_col2:
        st.info("💡 **피드백 루프 작동 원리**: AI 추천 수량과 다르게 입력된 점주의 최종 발주량 수치는 SQLite DB로 자동 적재되며, 실제 판매 데이터와 결합되어 점주 고유의 발주 보정 성향 및 오차 패턴을 재학습하는 파이프라인의 핵심 데이터로 수집됩니다.")

def render_chart(forecast_df):
    st.markdown('<div class="sec-title">📊 실시간 기상/상권 피처 반응 시각화</div>', unsafe_allow_html=True)
    
    # Sort strictly by product ID in descending order
    # Descending order puts product "P01" (도시락) at the top of horizontal bar charts
    chart_df = forecast_df.sort_values(by="id", ascending=False)
    
    # Calculate real-time weather delta tags for AI Expected Sales
    delta_texts = []
    for _, row in chart_df.iterrows():
        base = row["base_sales"]
        curr = row["expected_sales"]
        pct = int(round(((curr - base) / base) * 100))
        if pct > 0:
            delta_texts.append(f" {curr:.1f}개 (+{pct}% ▲)")
        elif pct < 0:
            delta_texts.append(f" {curr:.1f}개 ({pct}% ▼)")
        else:
            delta_texts.append(f" {curr:.1f}개 (0%)")
            
    chart_df["delta_text"] = delta_texts
    
    fig = go.Figure()
    
    # 1. Add scatter mark for Normal Baseline Sales (gray vertical ticks)
    fig.add_trace(go.Scatter(
        y=chart_df["name"],
        x=chart_df["base_sales"],
        mode='markers',
        name='평시 기준 수요',
        marker=dict(
            symbol='line-ns-open',
            size=16,
            color='#64748b',
            line=dict(width=3, color='#475569')
        ),
        hovertemplate="<b>%{y}</b><br>평시 기준수요: <b>%{x}개</b><extra></extra>"
    ))
    
    # 2. Add bar for AI Expected Sales (Teal color) - continuously sliding floats
    fig.add_trace(go.Bar(
        y=chart_df["name"],
        x=chart_df["expected_sales"],
        name="AI 예상 판매량 (수요)",
        orientation='h',
        marker=dict(
            color='#0ea5e9', # ocean blue
            line=dict(color='rgba(14, 165, 233, 0.2)', width=1)
        ),
        text=chart_df["delta_text"],
        textposition='outside',
        textfont=dict(color='#0f172a', size=10, family='Inter', weight='bold'),
        hovertemplate="<b>%{y}</b><br>AI 예상수요: <b>%{x:.1f}개</b><extra></extra>"
    ))
    
    # 3. Add bar for AI Recommended Orders (Violet color)
    fig.add_trace(go.Bar(
        y=chart_df["name"],
        x=chart_df["recommended_order"],
        name="최적 추천 발주량",
        orientation='h',
        marker=dict(
            color='#8b5cf6', # purple/violet
            line=dict(color='rgba(139, 92, 246, 0.2)', width=1)
        ),
        text=chart_df["recommended_order"].apply(lambda x: f" {x}개"),
        textposition='outside',
        textfont=dict(color='#6d28d9', size=10, family='Inter', weight='bold'),
        hovertemplate="<b>%{y}</b><br>추천 발주량: <b>%{x}개</b><extra></extra>"
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        barmode='group', # Grouped bars side-by-side
        bargap=0.18,      # Gap between product groups
        bargroupgap=0.05, # Gap between bars in a group
        xaxis=dict(
            title=dict(text="수량 (개)", font=dict(color='#475569', size=11)),
            tickfont=dict(color='#475569', size=10),
            gridcolor='#e2e8f0', # slate grid line for light mode readability
            zerolinecolor='#cbd5e1',
            side='bottom',
            range=[0, max(chart_df["expected_sales"].max(), chart_df["recommended_order"].max()) * 1.25] # make room for tags
        ),
        yaxis=dict(
            tickfont=dict(color='#0f172a', size=11, family='Inter', weight='bold'),
            gridcolor='rgba(0,0,0,0)'
        ),
        margin=dict(l=85, r=45, t=10, b=40),
        height=380,
        showlegend=True,
        legend=dict(
            font=dict(color='#0f172a', size=10),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        dragmode=False
    )
        
    render_html('<div class="glass-card" style="padding: 16px;">')
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    render_html('</div>')

def render_reasoning(forecast_df):
    st.markdown('<div class="sec-title">🧠 AI 발주 판단 세부 근거 (Decision Reasoning)</div>', unsafe_allow_html=True)
    
    render_html('<div class="glass-card" style="padding: 20px;">')
    render_html("""
    <div class="rules-header">
        <span>💡 상품별 기상/상권/주말 보정 요인 및 가설 분석</span>
    </div>
    """)
    
    for _, row in forecast_df.iterrows():
        # Display each item reasons
        render_html(f"""
        <div class="rules-item">
            <div style="display: flex; flex-direction: column; text-align: left;">
                <span style="font-weight: 700; color: #0f172a;">{row['name']} <span style="font-size: 0.72rem; color: #475569; font-weight: normal;">({row['category']})</span></span>
                <span style="font-size: 0.76rem; color: #475569; margin-top: 3px;">{row['reason']}</span>
            </div>
            <div style="display: flex; flex-direction: column; align-items: flex-end;">
                <span class="rules-tag" style="background: rgba(139, 92, 246, 0.05); color: #6d28d9;">위험도: {row['disposal_risk']} (안전재고 {row['safety_stock']}개)</span>
                <span class="rules-val" style="color: #0f172a;">ML {row['expected_sales']}개 / 추천 {row['recommended_order']}개</span>
            </div>
        </div>
        """)
        
    render_html('</div>')

def render_executive_report(forecast_df, weather, store_name, district, temp):
    st.markdown('<div class="sec-title">📄 AI 자동 작성 종합 발주 분석 리포트</div>', unsafe_allow_html=True)
    
    danger_items = forecast_df[forecast_df["status"] == "품절 위험"]
    waste_items = forecast_df[forecast_df["status"] == "폐기 우려"]
    top_orders = forecast_df.sort_values(by="recommended_order", ascending=False).head(3)
    top_orders = top_orders[top_orders["recommended_order"] > 0]
    
    # 1. Compose dynamic report paragraph
    intro = f"금일 **{store_name}** 점포는 외부 기상 여건(<b>날씨: {weather} / 기온: {temp}℃</b>)과 <b>{district} 상권</b>의 요일별 유동인구 이동 패턴이 결합된 형태를 띠고 있습니다."
    
    # Weather specifics
    if weather == "비":
        weather_analysis = "전체적으로 강수 조건이 감지되어 잡화류 중 '우산'의 수요가 극대화되는 시점입니다. 아울러 야외 활동이 위축되고 습도가 증가함에 따라 뜨거운 국물류 간식인 '컵라면' 및 편의점 간편식인 '도시락'의 실내 수요 집중 현상이 강력하게 반영되고 있습니다. 반면 차가운 유제품 빙과류는 비로 인한 체감 기온 저하로 단기 위축세를 보입니다."
    elif weather == "폭염":
        weather_analysis = "평균 온도가 30도를 웃도는 혹서기 환경 영향에 따라 얼음컵, 생수, 아이스 아메리카노 등 수분 보충 및 차가운 음료 제품군의 예상 판매량이 급격하게 증가하는 양상을 보이고 있습니다. 반면 고온 환경으로 인해 뜨겁게 조리되는 컵라면 계열의 식사 대용품 판매량은 큰 폭의 기피 경향이 뚜렷하게 관측됩니다."
    else:
        weather_analysis = "완만한 맑음 상태가 지속됨에 따라 빙과류(아이스크림) 및 시원한 주류(맥주)의 상시 소비 패턴이 균형감 있게 활성화되는 기조를 나타내고 있습니다."
        
    # Expiration specifics
    fresh_warning = ""
    if not waste_items.empty:
        w_names = ", ".join([f"'{item['name']}'" for _, item in waste_items.iterrows()])
        fresh_warning = f"특히, 유통기한이 극히 짧은 신선식품군 중 {w_names} 품목은 현재 보유 재고가 일일 AI 수요 예측량을 과도하게 초과하고 있어, <b>추가 발주를 긴급 제한하고 폐기 위험 관리 모드</b>로 진입해야 합니다."
    else:
        fresh_warning = "유통기한에 영향을 많이 받는 도시락 및 샌드위치 등 신선 식품(Fresh Food)군의 보유 잔고 수준은 오늘 예측 수요량 대비 안정적인 안전재고 범위 내에서 조율되고 있습니다."
        
    # Top orders recommendations
    reorder_list_html = ""
    if not top_orders.empty:
        reorder_list_html = "<ul>"
        for _, row in top_orders.iterrows():
            reason_tip = ""
            if row["name"] == "우산" and weather == "비":
                reason_tip = " (우천 시 최우선 권장)"
            elif row["shelf_life_type"] == "FF":
                reason_tip = " (폐기 위험 고려 타이트한 안전재고 반영)"
            else:
                reason_tip = f" (보관성 높음, 안전재고 {row['safety_stock']}개 확보 추천)"
                
            reorder_list_html += f"<li><b>{row['name']}</b>: {row['recommended_order']}개 신규 발주 권장{reason_tip}</li>"
        reorder_list_html += "</ul>"
    else:
        reorder_list_html = "금일은 매장 재고 잔여분이 충분하여 신규 추가 발주가 시급한 3대 대표 품목이 잡히지 않았습니다."
        
    # Render final glassmorphic report sheet
    render_html(f"""
    <div class="glass-card executive-report">
        <div class="report-title">
            <span>🏪 AI Smart Order Executive Report</span>
        </div>
        <p class="report-p">
            {intro}<br><br>
            {weather_analysis}
        </p>
        <div class="report-title" style="border-bottom:none; margin-top:20px; font-size:1rem; margin-bottom:8px;">
            <span>⚠️ 재고 위협 및 폐기 경보 진단</span>
        </div>
        <p class="report-p" style="color: #b45309; font-weight: 600;">
            {fresh_warning}
        </p>
        <div class="report-title" style="border-bottom:none; margin-top:20px; font-size:1rem; margin-bottom:8px;">
            <span>💜 내일 자 최적 발주 권장 3대 품목</span>
        </div>
        <div class="report-p">
            {reorder_list_html}
        </div>
    </div>
    """)

def render_feedback_analysis_tab():
    st.markdown('<div class="sec-title">📈 점주 피드백 수집 이력 및 모델 순응도 분석</div>', unsafe_allow_html=True)
    
    # Fetch metrics
    metrics = get_feedback_metrics()
    history_df = get_feedback_history()
    
    if metrics["total_items"] == 0:
        st.info("💡 아직 누적된 점주 발주 확정 이력이 없습니다. 상단 탭에서 발주량을 조정하고 '최종 발주 수량 확정'을 실행하시면 피드백 지표 분석이 활성화됩니다.")
        return
        
    kpi_cols = st.columns(3)
    with kpi_cols[0]:
        render_html(f"""
        <div class="glass-card" style="margin-bottom: 0px; padding: 20px;">
            <div class="metric-hdr">🤝 누적 발주 품목 수</div>
            <div class="metric-num" style="color: #2563eb;">{metrics['total_items']}<span class="unit" style="color: #2563eb;">건</span></div>
            <div class="metric-subtext">SQLite DB에 기록된 전체 최종 발주 피드백 로그</div>
        </div>
        """)
        
    with kpi_cols[1]:
        render_html(f"""
        <div class="glass-card" style="margin-bottom: 0px; padding: 20px;">
            <div class="metric-hdr">🎯 AI 추천 채택률 (Adoption)</div>
            <div class="metric-num" style="color: #059669;">{metrics['acceptance_rate']}<span class="unit" style="color: #059669;">%</span></div>
            <div class="metric-subtext">점주가 수정을 거치지 않고 추천 그대로 발주한 비율</div>
        </div>
        """)
        
    with kpi_cols[2]:
        render_html(f"""
        <div class="glass-card" style="margin-bottom: 0px; padding: 20px;">
            <div class="metric-hdr">📊 AI 추천 오차 강도 (MAD)</div>
            <div class="metric-num" style="color: #db2777;">{metrics['avg_deviation']}<span class="unit" style="color: #db2777;">개</span></div>
            <div class="metric-subtext">점주 수정 수량과 AI 추천 수량의 평균 절대 오차 수치</div>
        </div>
        """)
        
    st.write("")
    
    col1, col2 = st.columns([6, 4])
    
    with col1:
        st.subheader("📝 최근 발주 최종 확정 이력 (SQLite Raw Logs)")
        
        # Display the logs nicely
        display_history = history_df[[
            "timestamp", "date", "store_id", "product_id", 
            "predicted_sales_qty", "safety_stock", "current_stock", 
            "recommended_order_qty", "owner_adjusted_qty"
        ]].copy()
        
        display_history.columns = [
            "등록 시각", "대상 일자", "점포", "상품 ID", 
            "AI 예상수요", "안전재고", "현재고", "AI 추천량", "점주 최종발주량"
        ]
        
        st.dataframe(display_history, use_container_width=True, hide_index=True)
        
    with col2:
        st.subheader("📊 발주량 조정 및 수렴 차이")
        
        # Render Comparison chart between Recommended vs Owner Adjusted
        chart_df = history_df.head(20).copy() # last 20 records
        
        if not chart_df.empty:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                y=chart_df.index,
                x=chart_df["recommended_order_qty"],
                mode='markers+lines',
                name='AI 추천 발주량',
                line=dict(color='#8b5cf6', width=2),
                marker=dict(size=7, color='#8b5cf6')
            ))
            
            fig.add_trace(go.Scatter(
                y=chart_df.index,
                x=chart_df["owner_adjusted_qty"],
                mode='markers+lines',
                name='점주 최종 발주량',
                line=dict(color='#db2777', width=2, dash='dash'),
                marker=dict(size=7, color='#db2777')
            ))
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    title="발주량 (개)",
                    tickfont=dict(color='#475569', size=10),
                    gridcolor='#e2e8f0',
                    zerolinecolor='#cbd5e1'
                ),
                yaxis=dict(
                    title="기록 인덱스",
                    tickfont=dict(color='#475569', size=10),
                    gridcolor='#e2e8f0'
                ),
                margin=dict(l=40, r=20, t=10, b=40),
                height=260,
                legend=dict(
                    font=dict(color='#0f172a', size=10),
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.caption("차트를 그릴 데이터가 부족합니다.")
            
def render_footer():
    render_html("""
    <div style="text-align: center; margin-top: 40px; padding: 20px 0; border-top: 1px solid rgba(226, 232, 240, 0.8); color: #475569; font-size: 0.78rem; font-weight: 500;">
        본 서비스는 Scikit-Learn Random Forest Regressor 모델을 장착한 실전형 수요예측 & 자동 발주 추천 서비스 플랫폼입니다.<br>
        누적된 점주 피드백 데이터는 점포 고유의 판매 성향을 기계 학습하는 데 완전하게 재활용됩니다.<br>
        Convenience Smart Demand forecasting System | Powered by Antigravity AI Engine
    </div>
    """)

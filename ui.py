import streamlit as st
import datetime
import pandas as pd
import plotly.graph_objects as go
from config import WEATHER_OPTIONS, DISTRICT_OPTIONS
from database import save_recommendation_feedback, get_feedback_history, get_feedback_metrics
from validation import detect_order_anomalies, FRESH_FOOD_CATEGORY_LABEL


def init_order_session_state():
    """발주 확정·이상치 팝업 관련 session_state 초기화."""
    if "show_warning_modal" not in st.session_state:
        st.session_state.show_warning_modal = False
    if "pending_order_payload" not in st.session_state:
        st.session_state.pending_order_payload = None
    if "anomaly_items" not in st.session_state:
        st.session_state.anomaly_items = None
    if "order_submit_success" not in st.session_state:
        st.session_state.order_submit_success = False


def _build_order_items(forecast_df):
    """이상치 탐지용 발주 비교 데이터 생성."""
    items = []
    for _, row in forecast_df.iterrows():
        items.append({
            "product_id": row["id"],
            "product": row["name"],
            "category": row["category"],
            "shelf_life_type": row.get("shelf_life_type", ""),
            "predicted": int(row["recommended_order"]),
            "actual": int(st.session_state.adjusted_order[row["id"]]),
            "predicted_sales": float(row["expected_sales"]),
            "safety_stock": int(row["safety_stock"]),
            "current_stock": int(row["current_stock"]),
            "recommended_order": int(row["recommended_order"]),
            "adjusted_order": int(st.session_state.adjusted_order[row["id"]]),
        })
    return items


def _build_save_payload(forecast_df, date_str, store_id):
    """SQLite 저장용 페이로드 생성."""
    payload = []
    for _, row in forecast_df.iterrows():
        p_id = row["id"]
        payload.append({
            "date_str": date_str,
            "store_id": store_id,
            "product_id": p_id,
            "predicted_sales": float(row["expected_sales"]),
            "safety_stock": int(row["safety_stock"]),
            "current_stock": int(row["current_stock"]),
            "recommended_order": int(row["recommended_order"]),
            "adjusted_order": int(st.session_state.adjusted_order[p_id]),
        })
    return payload


def _persist_order_feedback(payload):
    """확정된 발주 피드백을 SQLite에 저장."""
    for item in payload:
        save_recommendation_feedback(
            date_str=item["date_str"],
            store_id=item["store_id"],
            product_id=item["product_id"],
            predicted_sales=item["predicted_sales"],
            safety_stock=item["safety_stock"],
            current_stock=item["current_stock"],
            recommended_order=item["recommended_order"],
            adjusted_order=item["adjusted_order"],
        )
    st.session_state.order_submit_success = True
    st.session_state.show_warning_modal = False
    st.session_state.pending_order_payload = None
    st.session_state.anomaly_items = None


def _severity_label(severity):
    return {"low": "Low", "medium": "Medium", "high": "High"}.get(severity, "Low")



def _render_anomaly_items_html(anomaly_items):
    """팝업 내부 이상치 상품 카드 HTML 생성."""
    cards = []
    for item in anomaly_items:
        is_ff = item.get("fresh_food_warning") or item.get("category") == FRESH_FOOD_CATEGORY_LABEL
        card_class = "anomaly-item-card fresh-food-card" if is_ff else f"anomaly-item-card severity-{item['severity']}"
        diff_sign = "+" if item["diff_percent"] > 0 else ""
        ff_badges = ""
        if is_ff:
            ff_badges = """
                <span class="anomaly-badge ff-badge">FRESH FOOD</span>
                <span class="anomaly-badge waste-badge">폐기 고위험</span>
            """
        ff_notice = ""
        if is_ff and item["absolute_diff"] > 0:
            ff_notice = """
                <p class="anomaly-ff-notice">
                    ⚠ 신선식품은 폐기 위험이 높아 과다 발주에 주의가 필요합니다.
                </p>
            """
        icon = "🍱" if is_ff else "📦"
        cards.append(f"""
        <div class="{card_class}">
            <div class="anomaly-item-header">
                <span class="anomaly-product-name">{icon} {item["product"]}</span>
                <span class="anomaly-severity-tag severity-{item["severity"]}">{_severity_label(item["severity"])}</span>
            </div>
            <div class="anomaly-badge-row">{ff_badges}</div>
            <div class="anomaly-stats">
                <span>예측: <b>{item["predicted"]}개</b></span>
                <span>입력: <b>{item["actual"]}개</b></span>
                <span>차이: <b class="diff-{item["severity"]}">{diff_sign}{item["diff_percent"]:.0f}%</b></span>
            </div>
            {ff_notice}
        </div>
        """)
    return "".join(cards)


@st.dialog("⚠ 발주량 차이가 큽니다", width="large")
def render_anomaly_warning_dialog():
    """Glassmorphism 경고 팝업 — 이상치 발주 확인 후 저장 여부 결정."""
    anomaly_items = st.session_state.get("anomaly_items") or []

    render_html("""
    <div class="anomaly-modal-body">
        <p class="anomaly-modal-desc">
            AI 예측 대비 큰 차이가 있는 상품이 발견되었습니다.<br>
            실제 발주를 진행하시겠습니까?
        </p>
    </div>
    """)

    render_html(f"""
    <div class="anomaly-items-list">
        {_render_anomaly_items_html(anomaly_items)}
    </div>
    """)

    st.write("")
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.button("✏️ 수정하기", use_container_width=True, key="anomaly_edit_btn"):
            st.session_state.show_warning_modal = False
            st.session_state.pending_order_payload = None
            st.session_state.anomaly_items = None
            st.rerun()

    with btn_col2:
        if st.button("✅ 그대로 발주", use_container_width=True, type="primary", key="anomaly_confirm_btn"):
            payload = st.session_state.get("pending_order_payload")
            if payload:
                _persist_order_feedback(payload)
            st.rerun()


def render_html(html_str):
    cleaned = "".join([line.strip() for line in html_str.split("\n")])
    st.markdown(cleaned, unsafe_allow_html=True)

def render_store_location_profile(store_row):
    """Shows prototype location features without requiring live GPS integration."""
    st.markdown("---")
    st.subheader("📍 샘플 위치 피처")

    address = store_row.get("address", "샘플 주소 없음")
    area_type = store_row.get("store_area_type", store_row.get("trade_area_type", "일반상권"))
    latitude = float(store_row.get("latitude", 0.0))
    longitude = float(store_row.get("longitude", 0.0))

    st.caption("실제 GPS/API 연동 전 단계로, CSV에 저장된 샘플 위치 피처를 사용합니다.")
    st.markdown(f"**{area_type}** · {address}")
    st.caption(f"샘플 좌표: {latitude:.4f}, {longitude:.4f}")

    loc_col1, loc_col2 = st.columns(2)
    with loc_col1:
        st.metric("학교", f"{int(store_row.get('school_count', 0))}곳")
        st.metric("오피스", f"{int(store_row.get('office_count', 0))}곳")
        st.metric("상업밀도", f"{float(store_row.get('commercial_density', 0.0)):.2f}")
    with loc_col2:
        st.metric("병원", f"{int(store_row.get('hospital_count', 0))}곳")
        st.metric("지하철", f"{int(store_row.get('subway_distance', 0))}m")
        st.metric("주거비율", f"{float(store_row.get('residential_ratio', 0.0)):.2f}")

def render_sidebar(store_df):
    with st.sidebar:
        st.markdown('<div style="text-align: center; padding: 10px 0;"><h3 style="font-family: \'Outfit\', sans-serif; color: #0f172a; margin-bottom: 5px;">🏪 AI Smart Order</h3><p style="color: #6d28d9; font-size: 0.82rem; font-weight: 600;">데이터 기반 수요예측 & 자동 발주</p></div>', unsafe_allow_html=True)
        st.markdown("---")
        
        st.subheader("⚙️ 상권 및 점포 설정")
        
        # Store selection
        store_options = {
            row["store_id"]: f"{row['store_name']} ({row.get('store_area_type', row['trade_area_type'])})"
            for _, row in store_df.iterrows()
        }
        selected_store_id = st.selectbox(
            "📍 대상 점포 선택",
            options=list(store_options.keys()),
            format_func=lambda x: store_options[x]
        )
        
        selected_store_row = store_df[store_df["store_id"] == selected_store_id].iloc[0]
        district = selected_store_row["trade_area_type"]
        render_store_location_profile(selected_store_row)
        
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

def render_header(date_str, store_name, weather, district, temp, store_area_type=None):
    area_text = f"{district} / {store_area_type}" if store_area_type else district
    render_html(f"""
    <div class="header-container">
        <span class="badge-ai">AI SMART ORDER MVP</span>
        <h1 class="main-title">🏪 {store_name} 스마트 발주 추천</h1>
        <p class="subtitle">분석일자: <b>{date_str}</b> | 날씨: <b>{weather} ({temp}℃)</b> | 상권 특성: <b>{area_text}</b></p>
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
    init_order_session_state()

    st.markdown('<div class="sec-title">📋 상품별 예측 상세 정보 및 발주 수량 조정</div>', unsafe_allow_html=True)
    
    # 1. Prepare display DataFrame for Streamlit Editor
    display_df = forecast_df.copy()
    
    # Populate the initial owner adjusted column as recommended orders
    if "adjusted_order" not in st.session_state:
        st.session_state.adjusted_order = {row["id"]: int(row["recommended_order"]) for _, row in display_df.iterrows()}
        
    display_df["adjusted_order"] = display_df["id"].map(st.session_state.adjusted_order)
    
    # Format columns for premium reading layout
    display_df["promotion_display"] = display_df["promotion_type"].apply(
        lambda x: "-" if str(x).lower() in ["none", "nan", "", "nan_value"] else str(x)
    )
    display_df["discount_display"] = display_df["discount_rate"].apply(
        lambda x: "-" if float(x) == 0.0 else f"{int(round(x * 100))}%"
    )
    
    # Format columns for nice reading
    display_df_viewer = display_df[[
        "id", "category", "name", "promotion_display", "discount_display", "current_stock", "safety_stock", 
        "ml_expected", "rule_expected", "recommended_order", "adjusted_order", "status"
    ]]
    
    # Customize column metadata
    edited_df = st.data_editor(
        display_df_viewer,
        column_config={
            "id": st.column_config.TextColumn("코드", disabled=True),
            "category": st.column_config.TextColumn("카테고리", disabled=True),
            "name": st.column_config.TextColumn("상품명", disabled=True),
            "promotion_display": st.column_config.TextColumn("🎁 프로모션 여부", disabled=True),
            "discount_display": st.column_config.TextColumn("🏷️ 할인율", disabled=True),
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

    if "moving_average_7d" in display_df.columns:
        with st.expander("🕐 시간·요일별 수요 피처 (ML·발주에 반영됨)", expanded=False):
            temporal_cols = [
                "name", "hour", "day_label", "is_weekend", "is_holiday",
                "previous_day_sales", "previous_week_sales",
                "moving_average_7d", "moving_average_28d",
                "demand_commute_morning", "demand_lunch", "demand_commute_evening", "demand_night",
                "peak_period", "temporal_mult",
            ]
            avail = [c for c in temporal_cols if c in display_df.columns]
            tview = display_df[avail].copy()
            rename_map = {
                "name": "상품",
                "hour": "hour (피크)",
                "day_label": "day_of_week",
                "is_weekend": "is_weekend",
                "is_holiday": "is_holiday",
                "previous_day_sales": "previous_day_sales",
                "previous_week_sales": "previous_week_sales",
                "moving_average_7d": "moving_average_7d",
                "moving_average_28d": "moving_average_28d",
                "demand_commute_morning": "출근 수요",
                "demand_lunch": "점심 수요",
                "demand_commute_evening": "퇴근 수요",
                "demand_night": "야간 수요",
                "peak_period": "피크 시간대",
                "temporal_mult": "시간·요일 보정계수",
            }
            tview = tview.rename(columns={k: rename_map.get(k, k) for k in tview.columns})
            st.dataframe(tview, use_container_width=True, hide_index=True)

    # 발주 확정: 이상치 탐지 후 팝업 또는 즉시 저장
    if st.button(
        "🔥 최종 발주 수량 확정 및 피드백 전송",
        use_container_width=True,
        type="primary",
        key="submit_order_btn",
    ):
        st.session_state.order_submit_success = False
        order_items = _build_order_items(display_df)
        anomalies = detect_order_anomalies(order_items)

        if anomalies:
            st.session_state.anomaly_items = anomalies
            st.session_state.pending_order_payload = _build_save_payload(display_df, date_str, store_id)
            st.session_state.show_warning_modal = True
        else:
            _persist_order_feedback(_build_save_payload(display_df, date_str, store_id))

    # 이상치 경고 팝업 표시
    if st.session_state.get("show_warning_modal") and st.session_state.get("anomaly_items"):
        render_anomaly_warning_dialog()

    # 저장 성공 토스트
    if st.session_state.get("order_submit_success"):
        render_html("""
        <div class="feedback-success-banner">
            <div class="feedback-success-title">✅ 최종 발주가 성공적으로 접수되었습니다</div>
            <div class="feedback-success-desc">SQLite DB 기록 및 피드백 누적이 완료되었습니다.</div>
        </div>
        """)
        st.session_state.order_submit_success = False

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
            delta_texts.append(f"+{pct}% ▲")
        elif pct < 0:
            delta_texts.append(f"{pct}% ▼")
        else:
            delta_texts.append("0%")
            
    chart_df["delta_text"] = delta_texts
    
    fig = go.Figure()
    
    # 1. Add bar for AI Expected Sales (Teal color) - continuously sliding floats
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
        textfont=dict(color='#0f172a', size=9, family='Inter', weight='bold'),
        hovertemplate="<b>%{y}</b><br>AI 예상수요: <b>%{x:.1f}개</b><extra></extra>"
    ))
    
    # 2. Add bar for Normal Baseline Sales (Slate/Gray color)
    fig.add_trace(go.Bar(
        y=chart_df["name"],
        x=chart_df["base_sales"],
        name="전국 편의점 평균 수요",
        orientation='h',
        marker=dict(
            color='#94a3b8', # slate gray
            line=dict(color='rgba(148, 163, 184, 0.2)', width=1)
        ),
        text=chart_df["base_sales"].apply(lambda x: f"{x}개"),
        textposition='outside',
        textfont=dict(color='#475569', size=9, family='Inter', weight='bold'),
        hovertemplate="<b>%{y}</b><br>전국 편의점 평균수요: <b>%{x}개</b><extra></extra>"
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        barmode='group', # Grouped bars side-by-side
        bargap=0.22,      # Gap between product groups
        bargroupgap=0.08, # Gap between bars in a group
        xaxis=dict(
            title=dict(text="수량 (개)", font=dict(color='#475569', size=11)),
            tickfont=dict(color='#475569', size=10),
            gridcolor='#e2e8f0', # slate grid line for light mode readability
            zerolinecolor='#cbd5e1',
            side='bottom',
            range=[0, max(chart_df["expected_sales"].max(), chart_df["base_sales"].max()) * 1.25] # make room for tags
        ),
        yaxis=dict(
            tickfont=dict(color='#0f172a', size=11, family='Inter', weight='bold'),
            gridcolor='rgba(0,0,0,0)'
        ),
        margin=dict(l=85, r=45, t=10, b=40),
        height=480,
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
        
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def render_reasoning(forecast_df):
    st.markdown('<div class="sec-title">🧠 AI 발주 판단 세부 근거 (Decision Reasoning)</div>', unsafe_allow_html=True)
    
    html_lines = []
    html_lines.append('<div class="glass-card" style="padding: 20px;">')
    html_lines.append("""
    <div class="rules-header">
        <span>💡 상품별 기상/상권/주말 보정 요인 및 가설 분석</span>
    </div>
    """)
    
    for _, row in forecast_df.iterrows():
        # Display each item reasons
        html_lines.append(f"""
        <div class="rules-item" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid rgba(226, 232, 240, 0.5);">
            <div style="display: flex; flex-direction: column; text-align: left; flex: 1; min-width: 0; margin-right: 16px;">
                <span style="font-weight: 700; color: #0f172a;">{row['name']} <span style="font-size: 0.72rem; color: #475569; font-weight: normal;">({row['category']})</span></span>
                <span style="font-size: 0.76rem; color: #475569; margin-top: 3px; word-break: keep-all; word-wrap: break-word; line-height: 1.35;">{row['reason']}</span>
            </div>
            <div style="display: flex; flex-direction: column; align-items: flex-end; flex-shrink: 0; min-width: 145px; text-align: right;">
                <span class="rules-tag" style="background: rgba(139, 92, 246, 0.05); color: #6d28d9; white-space: nowrap;">위험도: {row['disposal_risk']} (안전재고 {row['safety_stock']}개)</span>
                <span class="rules-val" style="color: #0f172a; margin-top: 4px; font-weight: 600; white-space: nowrap;">ML {row['expected_sales']}개 / 추천 {row['recommended_order']}개</span>
            </div>
        </div>
        """)
        
    html_lines.append('</div>')
    
    # Render all contents inside a single unified container to prevent auto-closing empty grids
    render_html("\n".join(html_lines))

def render_executive_report(forecast_df, weather, store_name, district, temp, rainfall=0.0):
    st.markdown('<div class="sec-title">📄 AI 자동 작성 종합 발주 분석 리포트</div>', unsafe_allow_html=True)
    
    danger_items = forecast_df[forecast_df["status"] == "품절 위험"]
    waste_items = forecast_df[forecast_df["status"] == "폐기 우려"]
    top_orders = forecast_df.sort_values(by="recommended_order", ascending=False).head(3)
    top_orders = top_orders[top_orders["recommended_order"] > 0]
    
    # Determine the weather dynamically based on physical values to ensure real-time reaction to sliders
    if rainfall > 0.0:
        active_weather = "비"
    elif temp >= 30.0:
        active_weather = "폭염"
    else:
        active_weather = "맑음"
        
    # 1. Compose dynamic report paragraph
    intro = f"금일 **{store_name}** 점포는 외부 기상 여건(<b>날씨 상태: {active_weather} / 기온: {temp}℃ / 강수량: {rainfall}mm</b>)과 <b>{district} 상권</b>의 요일별 유동인구 이동 패턴이 결합된 형태를 띠고 있습니다."
    
    # Weather specifics
    if active_weather == "비":
        weather_analysis = f"전체적으로 강수 조건({rainfall}mm)이 감지되어 잡화류 중 '우산'의 수요가 극대화되는 시점입니다. 아울러 야외 활동이 위축되고 습도가 증가함에 따라 뜨거운 국물류 간식인 '컵라면' 및 편의점 간편식인 '도시락'의 실내 수요 집중 현상이 강력하게 반영되고 있습니다. 반면 차가운 유제품 빙과류는 비로 인한 체감 기온 저하로 단기 위축세를 보입니다."
    elif active_weather == "폭염":
        weather_analysis = f"평균 온도가 {temp}℃로 혹서기 기준(30℃)을 웃도는 혹서기 환경 영향에 따라 얼음컵, 생수, 아이스 아메리카노 등 수분 보충 및 차가운 음료 제품군의 예상 판매량이 급격하게 증가하는 양상을 보이고 있습니다. 반면 고온 환경으로 인해 뜨겁게 조리되는 컵라면 계열의 식사 대용품 판매량은 큰 폭의 기피 경향이 뚜렷하게 관측됩니다."
    else:
        weather_analysis = f"기온 {temp}℃의 완만한 맑음 상태가 지속됨에 따라 빙과류(아이스크림) 및 시원한 주류(맥주)의 상시 소비 패턴이 균형감 있게 활성화되는 기조를 나타내고 있습니다."
        
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
            if row["name"] == "우산" and active_weather == "비":
                reason_tip = f" (우천 강수량 {rainfall}mm 대응 최우선 권장)"
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
            
def render_temporal_demand_view(engine, store_id, date_str, forecast_df, district):
    """POINT 2: 시간대·요일별 수요 예측 — 명세 변수 시각화."""
    st.caption(
        "판매 데이터를 **hour · day_of_week · is_weekend · is_holiday** 및 "
        "**previous_day_sales · previous_week_sales · moving_average_7d/28d** 와 함께 분석하고, "
        "**출근·점심·퇴근·야간** 시간대별 수요를 Random Forest 예측·발주 추천에 반영합니다."
    )

    render_html("""
    <div class="glass-card temporal-pipeline-card">
        <div class="rules-header"><span>📌 시간·요일 수요 예측 파이프라인 (로직 반영)</span></div>
        <div class="temporal-pipeline-steps">
            <div class="pipeline-step"><span class="step-num">1</span>시간별 판매 CSV</div>
            <div class="pipeline-arrow">→</div>
            <div class="pipeline-step"><span class="step-num">2</span>hour / 요일 / 공휴일</div>
            <div class="pipeline-arrow">→</div>
            <div class="pipeline-step"><span class="step-num">3</span>MA7 · MA28 · 전일·전주</div>
            <div class="pipeline-arrow">→</div>
            <div class="pipeline-step"><span class="step-num">4</span>출근·점심·퇴근·야간</div>
            <div class="pipeline-arrow">→</div>
            <div class="pipeline-step"><span class="step-num">5</span>ML + 발주량 보정</div>
        </div>
    </div>
    """)

    feature_spec = pd.DataFrame([
        {"변수": "hour", "설명": "피크 판매 시각 (0–23)", "로직 반영": "RF 학습 피처 + 상권 보정"},
        {"변수": "day_of_week", "설명": "요일 (0=월 … 6=일)", "로직 반영": "RF 학습 피처"},
        {"변수": "is_weekend", "설명": "주말 여부 (0/1)", "로직 반영": "RF + 상권 주말 감쇠"},
        {"변수": "is_holiday", "설명": "공휴일 여부 (0/1)", "로직 반영": "RF + 공휴일 배수"},
        {"변수": "previous_day_sales", "설명": "전일 판매량", "로직 반영": "RF 학습 피처"},
        {"변수": "previous_week_sales", "설명": "전주 동일일 판매", "로직 반영": "RF 학습 피처"},
        {"변수": "moving_average_7d", "설명": "7일 이동평균", "로직 반영": "RF + MA7/MA28 비율 보정"},
        {"변수": "moving_average_28d", "설명": "28일 이동평균", "로직 반영": "RF + 발주 근거 문구"},
        {"변수": "출근·점심·퇴근·야간", "설명": "시간대별 예상 수요", "로직 반영": "상권 temporal_mult"},
    ])
    st.dataframe(feature_spec, use_container_width=True, hide_index=True)

    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    day_label = forecast_df["day_label"].iloc[0] if "day_label" in forecast_df.columns else ["월", "화", "수", "목", "금", "토", "일"][date_obj.weekday()]
    is_hol = int(forecast_df["is_holiday"].iloc[0]) if "is_holiday" in forecast_df.columns else 0
    is_wknd = int(forecast_df["is_weekend"].iloc[0]) if "is_weekend" in forecast_df.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("분석 요일 (day_of_week)", day_label)
    m2.metric("is_weekend", "예" if is_wknd else "아니오")
    m3.metric("is_holiday", "예" if is_hol else "아니오")
    m4.metric("상권", district)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**🛒 상품별 명세 변수 스냅샷**")
        snap_cols = [
            "name", "hour", "day_label", "is_weekend", "is_holiday",
            "previous_day_sales", "previous_week_sales",
            "moving_average_7d", "moving_average_28d", "expected_sales",
        ]
        avail = [c for c in snap_cols if c in forecast_df.columns]
        if avail:
            snap = forecast_df[avail].copy()
            snap.columns = [
                "상품", "hour", "요일", "주말", "공휴일",
                "전일판매", "전주판매", "MA7", "MA28", "최종 예상판매",
            ][: len(avail)]
            st.dataframe(snap, use_container_width=True, hide_index=True)

    with col_b:
        st.markdown("**⏰ 출근·점심·퇴근·야간 예상 수요 (상위 5 SKU)**")
        period_cols = ["name", "demand_commute_morning", "demand_lunch", "demand_commute_evening", "demand_night", "peak_period"]
        pavail = [c for c in period_cols if c in forecast_df.columns]
        if len(pavail) >= 2:
            top5 = forecast_df.nlargest(5, "expected_sales")[pavail].copy()
            top5.columns = ["상품", "출근(7–11)", "점심(11–14)", "퇴근(17–20)", "야간(21–24)", "피크"][: len(pavail)]
            st.dataframe(top5, use_container_width=True, hide_index=True)
            fig_period = go.Figure()
            period_labels = ["출근", "점심", "퇴근", "야간"]
            for _, row in top5.head(3).iterrows():
                vals = [float(row[c]) for c in top5.columns[1:5] if c in row.index]
                while len(vals) < 4:
                    vals.append(0.0)
                fig_period.add_trace(go.Bar(
                    name=str(row[top5.columns[0]]),
                    x=period_labels,
                    y=vals[:4],
                ))
            fig_period.update_layout(
                barmode="group",
                height=300,
                title="시간대별 수요 (예측 반영값)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(248,250,252,0.5)",
            )
            st.plotly_chart(fig_period, use_container_width=True, config={"displayModeBar": False})

    hourly_df = getattr(engine, "hourly_sales_df", None)
    if hasattr(engine, "ensure_hourly_sales_loaded"):
        engine.ensure_hourly_sales_loaded()
        hourly_df = getattr(engine, "hourly_sales_df", None)
    if hourly_df is not None and not hourly_df.empty:
        from temporal_features import hour_in_period, COMMUTE_PERIODS

        st.markdown("**📈 점포 시간대별 실제 판매 (최근 14일)**")
        h = hourly_df.copy()
        h["date"] = pd.to_datetime(h["date"])
        h = h[(h["store_id"] == store_id) & (h["date"] >= pd.to_datetime(date_str) - pd.Timedelta(days=14))]
        if not h.empty:
            period_totals = {}
            for pname in COMMUTE_PERIODS:
                mask = h["hour"].apply(lambda x, p=pname: hour_in_period(int(x), p))
                period_totals[pname] = float(h.loc[mask, "sales_qty"].sum())
            fig_commute = go.Figure(go.Bar(
                x=list(period_totals.keys()),
                y=list(period_totals.values()),
                marker_color=["#6366f1", "#8b5cf6", "#a855f7", "#c084fc"],
            ))
            fig_commute.update_layout(
                height=280,
                xaxis_title="시간대 구간",
                yaxis_title="판매량 합계 (개)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(248,250,252,0.5)",
            )
            st.plotly_chart(fig_commute, use_container_width=True, config={"displayModeBar": False})


def render_footer():
    render_html("""
    <div style="text-align: center; margin-top: 40px; padding: 20px 0; border-top: 1px solid rgba(226, 232, 240, 0.8); color: #475569; font-size: 0.78rem; font-weight: 500;">
        본 서비스는 Scikit-Learn Random Forest Regressor 모델을 장착한 실전형 수요예측 & 자동 발주 추천 서비스 플랫폼입니다.<br>
        누적된 점주 피드백 데이터는 점포 고유의 판매 성향을 기계 학습하는 데 완전하게 재활용됩니다.<br>
        Convenience Smart Demand forecasting System | Powered by Antigravity AI Engine
    </div>
    """)

def render_top_products_view():
    st.markdown('<div class="sec-title">🔥 실시간 인기 상품(Top 10) 트렌드 분석</div>', unsafe_allow_html=True)
    st.write("과거 판매 실적 데이터를 실시간 집계하여 도출된 판매 주기별 인기 품목 순위입니다.")
    
    sub_t1, sub_t2, sub_t3 = st.tabs(["📅 일간 인기 상품", "📅 주간 인기 상품", "📅 월간 인기 상품"])
    
    from logic import get_top_products
    
    for period, tab in zip(["daily", "weekly", "monthly"], [sub_t1, sub_t2, sub_t3]):
        with tab:
            top_df = get_top_products(period)
            if top_df.empty:
                st.info("💡 집계할 판매 데이터가 부족합니다.")
                continue
                
            top_df = top_df.copy()
            top_df.insert(0, "순위", range(1, len(top_df) + 1))
            top_df = top_df.rename(columns={
                "product_name": "상품명",
                "category": "카테고리",
                "sales_qty": "누적 판매량 (개)",
                "unit_price": "가격 (원)"
            })
            
            # Decorate ranks with emojis
            decorated_ranks = []
            for rank in top_df["순위"]:
                if rank == 1:
                    decorated_ranks.append(f"🥇 1위")
                elif rank == 2:
                    decorated_ranks.append(f"🥈 2위")
                elif rank == 3:
                    decorated_ranks.append(f"🥉 3위")
                else:
                    decorated_ranks.append(f"⭐ {rank}위")
            top_df["순위"] = decorated_ranks
            
            st.dataframe(
                top_df[["순위", "product_id", "상품명", "카테고리", "가격 (원)", "누적 판매량 (개)"]],
                use_container_width=True,
                hide_index=True
            )

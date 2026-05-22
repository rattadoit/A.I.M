import streamlit as st

def load_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@300;400;500;600;700;800&display=swap');

    /* Global Streamlit styling overrides for Light Theme */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
        font-family: 'Inter', sans-serif;
    }
    
    /* Top Header container with gorgeous soft light gradient */
    .header-container {
        background: linear-gradient(135deg, #eef2ff 0%, #faf5ff 100%);
        border-radius: 20px;
        padding: 35px 30px;
        border: 1px solid rgba(139, 92, 246, 0.18);
        box-shadow: 0 10px 40px 0 rgba(139, 92, 246, 0.04), inset 0 0 20px rgba(255, 255, 255, 0.6);
        margin-bottom: 30px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    
    .header-container::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(139, 92, 246, 0.04) 0%, transparent 60%);
        pointer-events: none;
    }
    
    .badge-ai {
        background: linear-gradient(90deg, #6d28d9 0%, #db2777 100%);
        color: #ffffff;
        padding: 5px 16px;
        border-radius: 30px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 15px;
        box-shadow: 0 4px 14px rgba(109, 40, 217, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.25);
    }
    
    .main-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.6rem;
        font-weight: 800;
        margin: 0 0 10px 0;
        background: linear-gradient(90deg, #1e1b4b 20%, #4c1d95 60%, #db2777 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }
    
    .subtitle {
        font-size: 1.05rem;
        color: #475569;
        margin: 0;
        font-weight: 400;
    }
    
    .subtitle b {
        color: #6d28d9;
    }

    /* Premium Light Glassmorphism Card Panels */
    .glass-card {
        background: rgba(255, 255, 255, 0.85) !important;
        border-radius: 18px !important;
        padding: 24px !important;
        border: 1px solid rgba(226, 232, 240, 0.9) !important;
        box-shadow: 0 8px 30px 0 rgba(148, 163, 184, 0.06) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        margin-bottom: 24px !important;
        transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease !important;
        color: #0f172a !important;
    }
    
    .glass-card:hover {
        border-color: rgba(139, 92, 246, 0.4) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 35px 0 rgba(139, 92, 246, 0.1) !important;
    }
    
    /* Elegant Metric Widget inside card */
    .metric-hdr {
        font-size: 0.82rem;
        font-weight: 600;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    
    .metric-hdr.danger {
        color: #ef4444;
    }
    
    .metric-num {
        font-family: 'Outfit', sans-serif;
        font-size: 2.3rem;
        font-weight: 700;
        color: #0f172a;
        margin: 12px 0 4px 0;
    }
    
    .metric-num.danger {
        color: #ef4444;
    }
    
    .metric-num .unit {
        font-size: 1.1rem;
        color: #475569;
        font-weight: 500;
        margin-left: 5px;
    }
    
    .metric-num.danger .unit {
        color: #ef4444;
    }
    
    .metric-subtext {
        font-size: 0.78rem;
        color: #64748b;
        line-height: 1.4;
    }
    
    /* Table Styling Override */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 5px;
        font-size: 0.92rem;
        color: #1e293b;
        background: rgba(255, 255, 255, 0.45);
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(226, 232, 240, 0.8);
    }
    
    .custom-table th {
        background-color: rgba(139, 92, 246, 0.08) !important;
        color: #5b21b6;
        text-align: left;
        padding: 14px 16px;
        font-weight: 600;
        letter-spacing: 0.5px;
        border-bottom: 2px solid rgba(139, 92, 246, 0.18);
    }
    
    .custom-table td {
        padding: 13px 16px;
        border-bottom: 1px solid rgba(226, 232, 240, 0.6);
        vertical-align: middle;
    }
    
    .custom-table tr:hover {
        background-color: rgba(139, 92, 246, 0.02);
    }
    
    .row-danger {
        background-color: rgba(239, 68, 68, 0.03);
        border-left: 4px solid #ef4444 !important;
    }
    
    .row-danger:hover {
        background-color: rgba(239, 68, 68, 0.06) !important;
    }
    
    .row-warning {
        background-color: rgba(245, 158, 11, 0.02);
        border-left: 4px solid #f59e0b !important;
    }
    
    .row-warning:hover {
        background-color: rgba(245, 158, 11, 0.05) !important;
    }
    
    .row-normal {
        border-left: 4px solid transparent;
    }
    
    .cat-tag {
        background: rgba(241, 245, 249, 0.8);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.72rem;
        color: #475569;
        font-weight: 500;
        border: 1px solid rgba(226, 232, 240, 0.8);
    }
    
    .prod-txt {
        font-weight: 600;
        color: #0f172a;
    }
    
    .order-qty {
        background: rgba(139, 92, 246, 0.1);
        color: #5b21b6;
        border: 1px solid rgba(139, 92, 246, 0.25);
        padding: 3px 9px;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    
    .order-zero {
        color: #94a3b8;
        font-weight: 400;
    }
    
    /* Badges */
    .badge-warn {
        background-color: rgba(239, 68, 68, 0.08);
        color: #dc2626;
        border: 1px solid rgba(239, 68, 68, 0.2);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    
    .badge-alert {
        background-color: rgba(245, 158, 11, 0.08);
        color: #d97706;
        border: 1px solid rgba(245, 158, 11, 0.2);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    
    .badge-ok {
        background-color: rgba(16, 185, 129, 0.08);
        color: #059669;
        border: 1px solid rgba(16, 185, 129, 0.2);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
    }
    
    /* Section Headers */
    .sec-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.3rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        gap: 10px;
        border-left: 4px solid #8b5cf6;
        padding-left: 12px;
    }
    
    /* Sidebar Layout styling for Light Theme */
    section[data-testid="stSidebar"] {
        background-color: #f1f5f9 !important;
        border-right: 1px solid #e2e8f0 !important;
    }
    
    section[data-testid="stSidebar"] hr {
        border-color: #cbd5e1 !important;
    }
    
    /* Text elements inside sidebar */
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] h3 {
        color: #0f172a !important;
    }

    /* Decision Reasoning Panel */
    .rules-card {
        background: rgba(139, 92, 246, 0.02) !important;
        border: 1px solid rgba(139, 92, 246, 0.15) !important;
        border-radius: 14px;
        padding: 20px;
        margin-top: 18px;
    }
    
    .rules-header {
        font-family: 'Outfit', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: #4c1d95;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .rules-item {
        font-size: 0.82rem;
        color: #334155;
        padding: 8px 0;
        border-bottom: 1px solid rgba(226, 232, 240, 0.8);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .rules-item:last-child {
        border-bottom: none;
    }
    
    .rules-tag {
        font-size: 0.72rem;
        background: rgba(139, 92, 246, 0.05);
        color: #6d28d9;
        padding: 3px 9px;
        border-radius: 12px;
        border: 1px solid rgba(139, 92, 246, 0.15);
        font-weight: 500;
    }
    
    .rules-val {
        color: #0f172a;
        font-weight: 600;
        font-size: 0.85rem;
        max-width: 70%;
        text-align: right;
    }
    
    /* Dynamic AI Executive Report styling in Light Mode */
    .executive-report {
        background: linear-gradient(135deg, rgba(238, 242, 255, 0.4) 0%, rgba(255, 255, 255, 0.9) 100%) !important;
        border: 1px solid rgba(139, 92, 246, 0.2) !important;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 6px 24px rgba(148, 163, 184, 0.06) !important;
    }
    
    .report-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.15rem;
        font-weight: 700;
        color: #4c1d95;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 6px;
        border-bottom: 1px solid rgba(139, 92, 246, 0.12);
        padding-bottom: 8px;
    }
    
    .report-p {
        font-size: 0.88rem;
        color: #334155;
        line-height: 1.6;
        margin-bottom: 12px;
    }
    
    .report-bullet {
        font-size: 0.85rem;
        color: #334155;
        line-height: 1.5;
        margin-left: 12px;
        margin-bottom: 6px;
        position: relative;
        padding-left: 15px;
    }
    
    .report-bullet::before {
        content: '•';
        position: absolute;
        left: 0;
        color: #7c3aed;
        font-weight: bold;
    }

    /* Custom high-contrast buttons */
    div.stButton > button {
        background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%) !important;
        color: #ffffff !important;
        border: none !important;
        padding: 8px 20px !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15) !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(139, 92, 246, 0.25) !important;
    }

    /* Tab styles for premium light theme */
    button[data-baseweb="tab"] {
        color: #475569 !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        background-color: transparent !important;
        border: none !important;
        transition: all 0.2s ease !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #8b5cf6 !important;
        font-weight: 700 !important;
        border-bottom: 2px solid #8b5cf6 !important;
    }
    </style>
    """, unsafe_allow_html=True)

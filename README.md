# 🏪 AI Smart Order - 편의점 AI 수요 예측 및 발주 자동화 시스템

> **데이터 기반의 기상/상권 시뮬레이션을 통해 품절과 폐기를 극적으로 최소화하는 실전형 스마트 발주 플랫폼**

본 시스템은 편의점 점포의 과거 판매 데이터와 기상청 관측 및 예측 데이터, 상권 정보를 융합하여 상품별 정밀 예견 수요를 도출하고, 이에 연계된 최적 발주량을 실시간으로 추천 및 수집하는 웹 기반 대시보드(MVP) 솔루션입니다.

---

## ✨ 주요 핵심 기능

### 1. ML (Random Forest) 기반 정밀 수요 예측
*   **다차원 피처 연동**: 요일(원핫 인코딩), 기온, 대기 습도, 강수 여부, 강수량, 상권 유형, 카테고리를 Feature로 주입하여 정밀 튜닝된 `RandomForestRegressor` 모델이 작동합니다.
*   **피처 누수(Feature Leakage) 방지**: 정교한 역사적 시점 분리를 거쳐 최근 7일 평균 판매량(`recent_7d_avg`)과 최근 4주 동일 요일 평균 판매량(`recent_4w_weekday_avg`)을 동적으로 연산하여 예측 정확도 **R² 97% 이상**을 달성했습니다.

### 2. 연속형 기상 반응 블렌딩 모델 (Gliding Weather-Sensitivity)
*   일반적인 의사결정나무 모델의 계단식(Step-wise) 변화 한계를 극복하기 위해 **상품별 연속형 기상 민감도 함수**를 설계했습니다.
*   사이드바의 외부 환경 시뮬레이터(온도, 습도, 강수량 슬라이더)를 드래그하는 즉시, 수요 예측 바 그래프가 소수점 단위로 미끄러지듯 실시간으로 매끄럽게 변동합니다.

### 3. 상품 속성별 맞춤형 안전재고 자동 차등화
*   **신선식품 (Fresh Food - 도시락, 샌드위치 등)**: 당일 미판매 시 전액 폐기 손실로 직결되므로 일일 AI 예측량의 **15%** 수준으로 안전재고를 매우 타이트하게 조율하여 폐기를 방지합니다.
*   **상온/보존성 식품 (Dry Goods - 생수, 컵라면, 맥주 등)**: 장기 보관이 가능하므로 품절 기회 비용 유실을 잡는 것이 핵심입니다. 예측 수요의 **60%** 이상으로 넉넉한 안전재고 버퍼를 제공합니다.
*   공식: `최종 추천 발주량 = max(0, 예상 판매량 + 맞춤 안전재고 - 현재 보유 재고)`

### 4. 실시간 증감율 & 평시 기준선 시각화 (Plotly)
*   **평시 기준선 (Baseline Ticks)**: 상품별 일반 표준 조건에서의 판매량 기준점을 회색 세로선 틱으로 표시해 현재 시뮬레이션 상태가 평소 대비 얼마나 증감했는지 한눈에 파악합니다.
*   **증감 태그 (Delta Tags)**: 예상 판매량 바 끝에 실시간으로 `+25% ▲` 혹은 `-15% ▼` 와 같은 퍼센트 태그가 동적 갱신되어 기상 변동 영향을 입체적으로 인지시킵니다.

### 5. SQLite3 기반 영속 피드백 루프 (Feedback Loop)
*   점주가 화면 그리드(`st.data_editor`)에서 발주 수량을 수동 조정하고 확정 버튼을 누르면, 모든 데이터(날씨, 점포, 추천량, 점주 조정 수량)가 **SQLite 로컬 DB**에 저장됩니다.
*   누적된 피드백을 기반으로 **추천 채택률(Adoption Rate)** 및 **평균 절대 편차(MAD)**를 실시간 시계열 분포 차트로 분석하고 피드백 루프 모니터링 환경을 제공합니다.

### 6. 다이내믹 AI 리포트 자동 작성기
*   룰 베이스 지능형 엔진이 내일 날씨 급변 요소, 품절 위험 TOP3 품목, 폐기 경고 FF 상품군을 정교하게 분석하여, **LLM이 직접 작성한 듯한 자연스러운 종합 분석 리포트**를 생성합니다.

---

## 🎨 테마 디자인 및 레이아웃
*   **화사한 프리미엄 라이트 테마 (Light Theme)**: 사용자 브라우저 기본 다크모드 설정을 완벽하게 재정의하여 라벤더 바이올렛 포인트와 화사한 쿨 슬레이트 톤의 통일감 있는 비주얼을 제공합니다.
*   **초현실주의 글래스모피즘 (Glassmorphism)**: 은은한 배경 블러 필터와 투명도 85%의 정밀한 카드 보더를 설계하여 눈의 피로를 낮추고 하이엔드 느낌을 극대화했습니다.

---

## 📁 폴더 및 파일 구조

```text
no.1/
├── .streamlit/
│   └── config.toml            # 라이트 테마 강제 정형화 설정 파일
├── app.py                     # Streamlit 어플리케이션 통합 엔트리
├── config.py                  # 데이터 기준 사양 및 상품 10대 마스터 프로필 정의
├── database.py                # 점주 수동 발주 피드백 수집용 SQLite3 컨트롤러
├── logic.py                   # Random Forest 학습 모델 & 기상 반응 Blending 엔진
├── ui.py                      # 글래스모피즘 컴포넌트, Plotly 그래프 및 데이터 에디터 렌더러
├── styles.py                  # 프리미엄 CSS 테마 시트
├── data_generator.py          # 학습 및 시뮬레이션을 위한 60일치 판매 역사 합성기
├── requirements.txt           # 시스템 패키지 의존성 파일
└── data/                      # CSV 저장소 및 데이터 명세
    ├── sample_sales.csv       # 합성된 60일치 점포 판매 이력 데이터 (1,800건)
    ├── sample_product.csv     # 상품 사양 정보
    ├── sample_store.csv       # 점포 기본 정보
    ├── sample_weather.csv     # 일자별 날씨 정보
    └── data_schema.md         # 데이터베이스 테이블 및 파일 스키마 명세서
```

---

## 🛠️ 설치 및 가동 방법

### 1. 의존 패키지 설치
Python 3.8+ 환경의 터미널 혹은 PowerShell을 열고 아래 패키지를 설치합니다.
```powershell
pip install -r requirements.txt
```

### 2. 가상 과거 판매 데이터 합성 (최초 1회 필수)
머신러닝 모델 학습을 위해 과거 60일치 점포 판매 데이터를 생성합니다.
```powershell
python data_generator.py
```
*(가동 성공 시 `data/` 폴더 내에 CSV 파일군이 자동으로 안착됩니다.)*

### 3. Streamlit 대시보드 구동
```powershell
python -m streamlit run app.py
```
구동이 완료되면 브라우저에서 즉시 **[http://localhost:8501](http://localhost:8501)** 주소로 연동되어 시스템을 체험하실 수 있습니다.

---

## ⚡ 기술 스택
*   **Frontend**: Streamlit Custom Glassmorphic Styling
*   **Styling**: Pure CSS + Translucent Frosted Glass Overlay
*   **AI Engine**: Scikit-Learn Random Forest Regressor
*   **Visualization**: Plotly Horizontal Grouped Bars + Dynamic Annotation Ticks
*   **Database**: SQLite3 Local Repository

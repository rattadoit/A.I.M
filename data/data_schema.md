# 편의점 AI 자동 발주 데이터베이스 및 CSV 파일 스키마 규격서

본 프로젝트는 편의점 점포별 판매 트렌드, 상품 마스터 데이터, 외부 날씨 환경 요인을 통합하여 AI 예측 모델의 피처(Feature)를 구성하며, 점주 피드백을 기록하는 데이터 테이블로 이루어져 있습니다.

---

## 1. product_info (상품 마스터 정보)
- **설명**: 취급 상품의 기본 마스터 정보 및 유통기한/폐기위험 속성
- **형태**: `data/sample_product.csv`

| 컬럼명 (Column) | 타입 (Type) | 필수 여부 | 설명 (Description) | 예시 (Example) |
| :--- | :--- | :--- | :--- | :--- |
| **product_id** | VARCHAR(10) | Primary Key | 상품 식별 고유 코드 | `"P01"` |
| **product_name** | VARCHAR(50) | Not Null | 상품명 (한글) | `"도시락"` |
| **category** | VARCHAR(20) | Not Null | 상품 카테고리 (식사, 음료, 잡화, 주류, 간식) | `"식사"` |
| **shelf_life_type** | VARCHAR(10) | Not Null | 유통기한 구분 (`FF` (신선식품, 짧음), `DRY` (보존성 높음)) | `"FF"` |
| **disposal_risk** | VARCHAR(10) | Not Null | 폐기 위험도 등급 (`HIGH`, `MEDIUM`, `LOW`) | `"HIGH"` |
| **unit_price** | INTEGER | Not Null | 상품 판매 단가 (원) | `4800` |

---

## 2. store_info (점포 기본 정보)
- **설명**: 점포 마스터 정보 및 위치 상권 특성
- **형태**: `data/sample_store.csv`

| 컬럼명 (Column) | 타입 (Type) | 필수 여부 | 설명 (Description) | 예시 (Example) |
| :--- | :--- | :--- | :--- | :--- |
| **store_id** | VARCHAR(10) | Primary Key | 점포 식별 고유 코드 | `"S001"` |
| **store_name** | VARCHAR(50) | Not Null | 점포명 | `"마포대학가점"` |
| **trade_area_type** | VARCHAR(10) | Not Null | 상권 유형 (`학교`, `오피스`, `주거지`) | `"학교"` |
| **region** | VARCHAR(20) | Not Null | 행정구역 (날씨 매칭용) | `"서울"` |
| **latitude** | FLOAT | Prototype | 샘플 점포 위도 (실제 GPS 연동 전 테스트용) | `37.5584` |
| **longitude** | FLOAT | Prototype | 샘플 점포 경도 (실제 GPS 연동 전 테스트용) | `126.9459` |
| **address** | VARCHAR(100) | Prototype | 샘플 점포 주소 | `"서울시 서대문구 대학가 인근"` |
| **school_count** | INTEGER | Prototype | 점포 반경 내 학교 수 샘플 값 | `6` |
| **hospital_count** | INTEGER | Prototype | 점포 반경 내 병원 수 샘플 값 | `1` |
| **office_count** | INTEGER | Prototype | 점포 반경 내 오피스 수 샘플 값 | `5` |
| **subway_distance** | INTEGER | Prototype | 가장 가까운 지하철역까지 거리(m) 샘플 값 | `280` |
| **commercial_density** | FLOAT | Prototype | 주변 상업시설 밀도 지수 샘플 값 (0~1) | `0.72` |
| **residential_ratio** | FLOAT | Prototype | 주변 주거지역 비율 샘플 값 (0~1) | `0.38` |
| **store_area_type** | VARCHAR(20) | Prototype | 위치 기반 세분화 상권 유형 샘플 값 | `"대학가"` |

> 현재 프로토타입은 실제 GPS 권한 요청, 지도 API, 지오코딩, 주변 시설 검색 API를 사용하지 않습니다. 위 위치 기반 컬럼은 CSV에 저장된 샘플 피처이며, 향후 GPS 연동 시 같은 컬럼 구조에 실제 계산값을 채우는 방식으로 확장합니다.

---

## 3. weather_daily (일자별 날씨 관측 정보)
- **설명**: 일자별 지역 날씨 정보
- **형태**: `data/sample_weather.csv`

| 컬럼명 (Column) | 타입 (Type) | 필수 여부 | 설명 (Description) | 예시 (Example) |
| :--- | :--- | :--- | :--- | :--- |
| **date** | DATE | Primary Key | 관측 일자 (YYYY-MM-DD) | `"2026-05-01"` |
| **region** | VARCHAR(20) | Primary Key | 대상 행정구역 | `"서울"` |
| **temperature** | FLOAT | Not Null | 평균 기온 (℃) | `24.5` |
| **feels_like** | FLOAT | Not Null | 체감온도 (℃) | `25.2` |
| **rainfall** | FLOAT | Not Null | 일일 강수량 (mm) (비가 안 오면 0) | `0.0` |
| **rainy** | INTEGER | Not Null | 비 여부 (0: 맑음/비 안 옴, 1: 비 옴) | `0` |
| **humidity** | FLOAT | Not Null | 평균 습도 (%) | `62.0` |

---

## 4. sales_history (과거 판매 실적 및 재고 데이터)
- **설명**: 점포별, 상품별 일자별 실제 판매, 폐기 및 품절 이력 (ML 모델의 정답(y) 및 핵심 피처(X) 생성용)
- **형태**: `data/sample_sales.csv`

| 컬럼명 (Column) | 타입 (Type) | 필수 여부 | 설명 (Description) | 예시 (Example) |
| :--- | :--- | :--- | :--- | :--- |
| **date** | DATE | FK, PK | 판매 영업 일자 (YYYY-MM-DD) | `"2026-05-01"` |
| **store_id** | VARCHAR(10) | FK, PK | 점포 식별 고유 코드 | `"S001"` |
| **product_id** | VARCHAR(10) | FK, PK | 상품 식별 고유 코드 | `"P01"` |
| **sales_qty** | INTEGER | Not Null | 실제 판매량 (개) (정답 데이터) | `38` |
| **stock_qty** | INTEGER | Not Null | 기초 당일 보유 재고량 (개) | `8` |
| **disposed_qty** | INTEGER | Not Null | 당일 영업 종료 후 최종 폐기 수량 (개) | `2` |
| **sold_out** | INTEGER | Not Null | 당일 품절 발생 여부 (0: 정상영업, 1: 조기품절) | `0` |
| **sold_out_time** | VARCHAR(10) | Nullable | 품절 발생 시각 (예: 18:30, 품절 안 되면 empty) | `""` |

---

## 5. order_recommendation_log (점주 최종 발주 확정 및 피드백 로그)
- **설명**: AI가 추천한 발주량과 점주가 실제 수동 조정한 이력을 트래킹하여 피드백 및 재학습 데이터 구축용
- **형태**: SQLite 데이터베이스 테이블 (`order_recommendation_log`)

| 컬럼명 (Column) | 타입 (Type) | 제약 조건 | 설명 (Description) | 예시 (Example) |
| :--- | :--- | :--- | :--- | :--- |
| **id** | INTEGER | Primary Key | 고유 레코드 인덱스 (자동 증가) | `1` |
| **timestamp** | TIMESTAMP | Default NOW | 발주 확정 등록 시각 | `"2026-05-22 21:05:00"` |
| **date** | DATE | Not Null | 발주 대상 타깃 날짜 (YYYY-MM-DD) | `"2026-05-23"` |
| **store_id** | VARCHAR(10) | Not Null | 점포 고유 코드 | `"S001"` |
| **product_id** | VARCHAR(10) | Not Null | 상품 고유 코드 | `"P01"` |
| **predicted_sales_qty** | FLOAT | Not Null | AI 예측 판매 수량 | `41.2` |
| **safety_stock** | INTEGER | Not Null | 반영된 안전재고량 | `2` |
| **current_stock** | INTEGER | Not Null | 발주 추천 시점의 보유 재고 | `7` |
| **recommended_order_qty**| INTEGER | Not Null | AI 최종 추천 발주량 | `36` |
| **owner_adjusted_qty** | INTEGER | Not Null | **점주가 실제로 수정한 수량 (피드백 핵심)** | `35` |
| **is_submitted** | INTEGER | Not Null | 최종 본사 전송 완료 여부 (1: 확정) | `1` |

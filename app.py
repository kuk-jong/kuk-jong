import streamlit as st
import pandas as pd
import numpy as np
import math

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="전남 무화과 경영 분석기", layout="wide")

st.title("🗺️ [전남] 무화과 연간 경영 분석 시스템")
st.markdown("겨울철 투자 분석뿐만 아니라, **여름 작기를 포함한 연간 총 소득**까지 예측해 드립니다.")
st.divider()

# --- [DATA] 지역 데이터 ---
REGION_DATA = {
    "영암군 (무화과 주산지)": {"base": 2.0, "amp": 8.0},
    "해남군": {"base": 2.2, "amp": 7.8},
    "목포시": {"base": 2.5, "amp": 7.5},
    "신안군": {"base": 3.0, "amp": 7.0},
    "진도군": {"base": 3.2, "amp": 6.8},
    "완도군": {"base": 3.5, "amp": 6.5},
    "무안군": {"base": 1.5, "amp": 8.2},
    "강진군": {"base": 2.0, "amp": 8.0},
    "장흥군": {"base": 1.8, "amp": 8.2},
    "여수시": {"base": 3.0, "amp": 7.0},
    "순천시": {"base": 1.5, "amp": 8.5},
    "광양시": {"base": 2.0, "amp": 8.0},
    "고흥군": {"base": 2.8, "amp": 7.2},
    "보성군": {"base": 1.0, "amp": 8.5},
    "나주시": {"base": 0.5, "amp": 9.0},
    "담양군": {"base": -0.5, "amp": 9.5},
    "곡성군": {"base": -1.0, "amp": 10.0},
    "구례군": {"base": -0.5, "amp": 9.8},
    "화순군": {"base": -1.0, "amp": 9.8},
    "장성군": {"base": -0.5, "amp": 9.5},
    "함평군": {"base": 1.0, "amp": 8.8},
    "영광군": {"base": 1.0, "amp": 8.8}
}

# --- 2. 사이드바: 폼(Form) 기반 입력 ---
with st.sidebar:
    with st.form(key='input_form'):
        st.header("📝 데이터 입력")
        st.info("데이터 입력 후 맨 아래 버튼을 누르세요.")

        # [0] 지역 선택
        with st.expander("0. 지역 선택", expanded=True):
            region_name = st.selectbox("전남 시·군 선택", list(REGION_DATA.keys()))
        
        # [1] 온실 규격
        with st.expander("1. 온실 규격", expanded=False):
            gh_type = st.radio("온실 형태", ["단동 (1동)", "연동 (여러 동 연결)"])
            span_count = st.number_input("연동 수", value=1 if gh_type=="단동 (1동)" else 3, step=1)
            gh_width = st.number_input("폭 (m)", value=6.0, step=0.5)
            gh_length = st.number_input("길이 (m)", value=50.0, step=1.0)
            gh_side_h = st.number_input("측고 (m)", value=2.0, step=0.2)
            gh_ridge_h = st.number_input("동고 (m)", value=3.5, step=0.2)
            
            floor_area_m2 = gh_width * gh_length * span_count
            floor_area_py = floor_area_m2 / 3.3

        # [2] 생산 목표 (여름/겨울 분리)
        with st.expander("2. 연간 생산 계획", expanded=False):
            st.markdown("**🌞 여름 작기 (기본)**")
            summer_total_yield = st.number_input("여름 총 생산량 (kg)", value=3000, step=100)
            # [추가] 여름 단가
            summer_price = st.number_input("여름 평균 단가 (원/kg)", value=6000, step=500)
            # [추가] 여름 경영비율 (간단 계산용)
            summer_cost_ratio = st.slider("여름철 경영비 비율 (%)", 10, 50, 30, help="매출액 중 비료, 인건비 등이 차지하는 비율")
            
            st.markdown("---")
            st.markdown("**⛄ 겨울 작기 (추가)**")
            winter_total_yield = st.number_input("겨울 예상 생산량 (kg)", value=1200, step=100)
            market_price = st.number_input("겨울 예상 단가 (원/kg)", value=18000, step=1000)

        # [3] 시설 투자
        with st.expander("3. 시설 투자비", expanded=False):
            cost_film = st.number_input("피복재 (3년)", value=200, step=50)
            cost_curtain = st.number_input("보온커튼 (5년)", value=1500, step=100)
            cost_heater = st.number_input("난방기 (10년)", value=500, step=100)
            cost_facility = st.number_input("기타 설비 (10년)", value=300, step=100)

        # [4] 에너지 설정
        with st.expander("4. 에너지 설정", expanded=False):
            energy_source = st.selectbox("사용 연료", ["면세유(경유)", "농사용 전기"])
            unit_fuel_cost = st.number_input("연료 단가 (원)", value=1100 if energy_source=="면세유(경유)" else 50)
            target_temp = st.slider("목표 온도 (℃)", 10, 20, 15)
            insul_type = st.selectbox("보온 등급", ["비닐 1겹 (U=5.5)", "비닐 2겹 (U=4.5)", "다겹보온커튼 (U=2.0)", "고효율 패키지 (U=1.5)"])

        st.write("---")
        submit_btn = st.form_submit_button(label='🚜 연간 분석 실행 (Click)', type="primary", use_container_width=True)


# --- 3. 알고리즘 및 결과 처리 ---

if submit_btn:
    
    # --- A. 겨울철 정밀 분석 (기존 로직) ---
    u_values = {"비닐 1겹 (U=5.5)": 5.5, "비닐 2겹 (U=4.5)": 4.5, "다겹보온커튼 (U=2.0)": 2.0, "고효율 패키지 (U=1.5)": 1.5}
    u_val = u_values[insul_type]
    
    # 표면적
    roof_height = gh_ridge_h - gh_side_h
    roof_slope_len = math.sqrt((gh_width/2)**2 + roof_height**2)
    area_roof = 2 * roof_slope_len * gh_length * span_count 
    area_side = 2 * gh_length * gh_side_h 
    one_end_wall = (gh_width * gh_side_h) + (0.5 * gh_width * roof_height)
    area_end = one_end_wall * 2 * span_count 
    surface_area = area_roof + area_side + area_end
    
    # 감가상각비
    d1 = cost_film / 3       
    d2 = cost_curtain / 5    
    d3 = cost_heater / 10    
    d4 = cost_facility / 10  
    depreciation = (d1 + d2 + d3 + d4) * 10000 
    
    # 겨울 시뮬레이션
    dates = pd.date_range('2025-11-01', '2026-02-28') 
    winter_revenue = 0
    winter_fuel_cost = 0
    
    eff = 0.85 if energy_source == "면세유(경유)" else 0.98
    calorific = 8500 if energy_source == "면세유(경유)" else 860
    daily_base_yield = winter_total_yield / 120
    
    region_info = REGION_DATA[region_name]
    base_t = region_info['base']
    amp_t = region_info['amp']

    for i, date in enumerate(dates):
        simulated_temp = base_t - (amp_t * np.sin(np.pi * i / 120)) 
        min_temp = simulated_temp + np.random.uniform(-2, 2)
        
        delta_t = max(target_temp - min_temp, 0)
        daily_load = surface_area * u_val * delta_t * 14
        needed = daily_load / (calorific * eff)
        winter_fuel_cost += needed * unit_fuel_cost
        
        season_factor = 1.0
        if date.month == 1: season_factor = 0.8
        elif date.month == 11 or date.month == 2: season_factor = 1.1
        daily_yield = daily_base_yield * season_factor
        winter_revenue += daily_yield * market_price

    # 정수 변환
    winter_revenue = int(winter_revenue)
    winter_fuel_cost = int(winter_fuel_cost)
    depreciation = int(depreciation)
    
    # 겨울 순수익 (겨울매출 - 난방비 - 연간감가상각)
    winter_net_profit = winter_revenue - winter_fuel_cost - depreciation

    # --- B. 여름철 및 연간 분석 (신규 로직) ---
    summer_revenue = summer_total_yield * summer_price
    summer_cost = summer_revenue * (summer_cost_ratio / 100) # 경영비율 적용
    summer_net_profit = summer_revenue - summer_cost
    
    # 연간 총합
    total_annual_revenue = summer_revenue + winter_revenue
    total_annual_profit = summer_net_profit + winter_net_profit
    
    # --- C. 결과 출력 ---
    st.header(f"📊 연간 경영 분석 리포트 ({region_name})")
    
    # 1. 겨울 투자 분석 (핵심)
    st.subheader("❄️ 1. 겨울 재배 투자 성적표")
    col1, col2, col3 = st.columns(3)
    col1.metric("겨울 매출", f"{winter_revenue/10000:,.0f} 만원")
    col2.metric("겨울 비용(난방+상각)", f"{(winter_fuel_cost+depreciation)/10000:,.0f} 만원")
    col3.metric("겨울 순이익", f"{winter_net_profit/10000:,.0f} 만원", 
                delta="투자 성공" if winter_net_profit > 0 else "투자 주의")
    
    # 2. 연간 총괄 (종합)
    st.subheader("📅 2. 연간 총 소득 (여름 + 겨울)")
    c1, c2, c3 = st.columns(3)
    c1.metric("연간 총 매출", f"{total_annual_revenue/10000:,.0f} 만원", help="여름 매출 + 겨울 매출")
    c2.metric("연간 총 순이익", f"{total_annual_profit/10000:,.0f} 만원", 
              delta=f"여름 대비 +{winter_net_profit/10000:,.0f}만원")
    
    # 소득 구성비 차트
    st.write("---")
    st.subheader("💰 소득 구조 시각화")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.caption("계절별 매출 비중")
        df_rev = pd.DataFrame({
            "계절": ["여름 작기", "겨울 작기"],
            "매출액": [summer_revenue, winter_revenue]
        })
        st.bar_chart(df_rev.set_index("계절"))
        
    with chart_col2:
        st.caption("비용 구조 분석")
        df_cost = pd.DataFrame({
            "항목": ["여름 경영비", "겨울 난방비", "시설 감가상각비"],
            "금액": [summer_cost, winter_fuel_cost, depreciation]
        })
        st.bar_chart(df_cost.set_index("항목"))

    # 최종 제언
    st.success(f"""
    **📢 최종 진단:**
    * 겨울 재배를 추가할 경우, 기존 여름 소득({int(summer_net_profit/10000):,}만원)에 더해
    **{int(winter_net_profit/10000):,}만원의 추가 이익**이 발생합니다.
    * 따라서 연간 총 소득은 **{int(total_annual_profit/10000):,}만원**으로 예상됩니다.
    """)

else:
    st.info("👈 왼쪽 메뉴에서 데이터를 입력하고 '분석 실행' 버튼을 눌러주세요.")

# ... (기존 코드 맨 끝) ...

st.write("---")
with st.expander("📚 분석 근거 및 데이터 출처 보기 (Reference)"):
    st.markdown("""
    ### 1. 기상 데이터 출처
    * **기상청 기상자료개방포털:** 전라남도 주요 시·군 1991~2020년 평년값(30년) 기준
    * 지역별 겨울철 평균 최저기온 및 기온 편차를 적용하여 시뮬레이션

    ### 2. 난방부하 산출 공식
    * **농촌진흥청 '원예시설 난방부하 산정 기준' 준용**
    * $Q = A \\times U \\times (T_{set} - T_{out}) \\times (1 - R)$
    * 단순 바닥면적이 아닌, **온실 표면적(지붕+측벽+마구리)**을 기하학적으로 정밀 계산

    ### 3. 에너지 기준
    * **면세유:** 저위발열량 8,500kcal/L, 효율 85% 가정
    * **전기:** 열당량 860kcal/kWh, 효율 98% 가정

    ### 4. 감가상각 기준
    * **농촌진흥청 농산물소득조사 분석 기준 적용 (정액법)**
    * 피복재(3년), 보온커튼(5년), 난방기/설비(10년)
    """)

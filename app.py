import streamlit as st
import pandas as pd
import numpy as np
import math

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="전남 무화과 경영 분석기", layout="wide")

st.title("🗺️ [전남] 무화과 겨울재배 경영 분석 시스템")
st.markdown("왼쪽 화살표(>)를 눌러 데이터를 입력하고 **[분석 실행]** 버튼을 누르세요.")
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
# ★핵심 변경★: st.form을 사용하여 입력 중 새로고침 방지
with st.sidebar:
    with st.form(key='input_form'):
        st.header("📝 데이터 입력")
        st.info("아래 내용을 모두 입력 후 맨 밑의 버튼을 누르세요.")

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
            
            # 면적 계산 (폼 내부에서는 실시간 출력이 안되므로 나중에 계산)
            floor_area_m2 = gh_width * gh_length * span_count
            floor_area_py = floor_area_m2 / 3.3

        # [2] 생산 목표
        with st.expander("2. 생산 목표", expanded=False):
            summer_total_yield = st.number_input("여름 총 생산량 (kg)", value=3000, step=100)
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
        # ★★★ 여기가 제일 중요합니다 ★★★
        # form_submit_button을 써야 입력이 완료된 후 한 번에 실행됩니다.
        submit_btn = st.form_submit_button(label='🚜 분석 실행 (Click)', type="primary", use_container_width=True)


# --- 3. 알고리즘 및 결과 처리 ---

# 버튼이 눌렸을 때만 아래 코드가 실행됨
if submit_btn:
    
    # --- 변수 정리 ---
    u_values = {"비닐 1겹 (U=5.5)": 5.5, "비닐 2겹 (U=4.5)": 4.5, "다겹보온커튼 (U=2.0)": 2.0, "고효율 패키지 (U=1.5)": 1.5}
    u_val = u_values[insul_type]
    
    # 1. 표면적 계산
    roof_height = gh_ridge_h - gh_side_h
    roof_slope_len = math.sqrt((gh_width/2)**2 + roof_height**2)
    area_roof = 2 * roof_slope_len * gh_length * span_count 
    area_side = 2 * gh_length * gh_side_h 
    one_end_wall = (gh_width * gh_side_h) + (0.5 * gh_width * roof_height)
    area_end = one_end_wall * 2 * span_count 
    surface_area = area_roof + area_side + area_end
    
    # 2. 감가상각비 계산
    d1 = cost_film / 3       
    d2 = cost_curtain / 5    
    d3 = cost_heater / 10    
    d4 = cost_facility / 10  
    depreciation = (d1 + d2 + d3 + d4) * 10000 
    
    # 3. 시뮬레이션
    dates = pd.date_range('2025-11-01', '2026-02-28') 
    total_rev = 0
    total_cost = 0
    
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
        total_cost += needed * unit_fuel_cost
        
        season_factor = 1.0
        if date.month == 1: season_factor = 0.8
        elif date.month == 11 or date.month == 2: season_factor = 1.1
            
        daily_yield = daily_base_yield * season_factor
        total_rev += daily_yield * market_price

    # 4. 결과 출력
    result_fuel_cost = int(total_cost)
    revenue = int(total_rev)
    depreciation = int(depreciation)
    net_profit = revenue - result_fuel_cost - depreciation
    
    # --- 화면 표시 ---
    st.header(f"📊 분석 리포트 ({region_name})")
    
    c1, c2 = st.columns(2)
    c1.metric("예상 매출액", f"{revenue/10000:,.0f} 만원")
    c2.metric("총 비용", f"{(result_fuel_cost+depreciation)/10000:,.0f} 만원")
    
    st.metric("예상 순수익", f"{net_profit/10000:,.0f} 만원", 
              delta="흑자" if net_profit > 0 else "적자")
    
    st.write("---")
    st.subheader("💸 비용 상세")
    
    df_cost = pd.DataFrame({
        "항목": ["난방비", "감가상각비"],
        "금액": [result_fuel_cost, depreciation]
    })
    st.bar_chart(df_cost.set_index("항목"))
    
    st.info(f"""
    **ℹ️ 온실 정보**
    * 바닥 면적: {floor_area_py:.1f}평
    * 난방 부하 표면적: {surface_area:.1f}㎡
    * 여름 대비 생산성: {(winter_total_yield/summer_total_yield*100):.1f}%
    """)

else:
    # 아직 버튼 안 눌렀을 때
    st.info("👈 왼쪽 사이드바에서 데이터를

import streamlit as st
import pandas as pd
import numpy as np
import math

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="무화과 정밀 경영 분석기 (Final+Region)", layout="wide")

st.title("🗺️ 지역 기후 데이터 기반 무화과 겨울재배 경영 분석")
st.markdown("""
**지역별 기온 데이터(최근 10년 평년값)**를 반영하여 더욱 정밀한 난방비를 예측합니다.
왼쪽 메뉴에서 **지역**을 선택하고 데이터를 입력하세요.
""")
st.divider()

# --- [DATA] 지역별 겨울철(11~2월) 기온 특성 데이터 ---
# 기상청 평년값(1991~2020) 기반 추정치 (단위: ℃)
# base_temp: 겨울철 평균 최저기온의 기준선
# cold_amp: 추위의 강도 (클수록 더 추움)
REGION_DATA = {
    "전남 영암 (주산지)": {"base": 2.0, "amp": 8.0},  # 비교적 온화
    "전남 해남": {"base": 2.5, "amp": 7.5},
    "전남 신안": {"base": 3.0, "amp": 7.0},         # 섬 지역이라 덜 추움
    "전남 나주": {"base": 0.5, "amp": 9.0},         # 내륙이라 더 추움
    "경남 진주": {"base": 0.0, "amp": 9.5},
    "충남 논산": {"base": -2.0, "amp": 11.0},
    "경기 파주 (비교용)": {"base": -6.0, "amp": 13.0} # 매우 추움
}

# --- 2. 사이드바: 데이터 입력 ---
with st.sidebar:
    st.header("📝 데이터 입력")
    st.info("화살표(>)를 눌러 각 항목을 입력하세요.")

    # [0] 지역 선택 (신규 추가)
    with st.expander("0. 지역 선택 (필수)", expanded=True):
        region_name = st.selectbox(
            "농장 위치를 선택하세요",
            list(REGION_DATA.keys())
        )
        st.caption(f"📍 **{region_name}**의 최근 기후 데이터를 불러옵니다.")

    # [1] 온실 규격
    with st.expander("1. 온실 규격 입력", expanded=False):
        gh_type = st.radio("온실 형태", ["단동 (1동)", "연동 (여러 동 연결)"])
        span_count = st.number_input("연동 수", value=1 if gh_type=="단동 (1동)" else 3, step=1, min_value=1)
        
        gh_width = st.number_input("폭 (m, 1동 기준)", value=6.0, step=0.5)
        gh_length = st.number_input("길이 (m)", value=50.0, step=1.0)
        
        gh_side_h = st.number_input("측고 (어깨높이 m)", value=2.0, step=0.2)
        gh_ridge_h = st.number_input("동고 (중앙높이 m)", value=3.5, step=0.2)

        floor_area_m2 = gh_width * gh_length * span_count
        floor_area_py = floor_area_m2 / 3.3
        st.write(f"📐 바닥: **{floor_area_py:.1f}평**")

    # [2] 생산 목표
    with st.expander("2. 생산 목표 설정", expanded=False):
        summer_total_yield = st.number_input(
            "🌞 평소(여름) 총 생산량 (kg)", 
            value=int(floor_area_py * 10), 
            step=100
        )
        
        winter_total_yield = st.number_input(
            "⛄ 겨울 작기 예상 총 생산량 (kg)", 
            value=int(summer_total_yield * 0.4), 
            step=100
        )
        
        if summer_total_yield > 0:
            ratio = (winter_total_yield / summer_total_yield) * 100
            st.caption(f"💡 여름 대비 **{ratio:.1f}%** 수준")
        
        market_price = st.number_input("겨울철 예상 단가 (원/kg)", value=18000, step=1000)

    # [3] 시설 투자
    with st.expander("3. 시설 투자 및 감가상각", expanded=False):
        cost_film = st.number_input("① 피복재 (3년)", value=200, step=50)
        cost_curtain = st.number_input("② 보온커튼 (5년)", value=1500, step=100)
        cost_heater = st.number_input("③ 난방기 (10년)", value=500, step=100)
        cost_facility = st.number_input("④ 기타 설비 (10년)", value=300, step=100)
        
        total_invest = cost_film + cost_curtain + cost_heater + cost_facility
        st.caption(f"💰 총 투자비: {total_invest:,} 만원")

    # [4] 에너지 설정
    with st.expander("4. 에너지 및 보온", expanded=False):
        energy_source = st.selectbox("사용 연료", ["면세유(경유)", "농사용 전기"])
        fuel_cost = st.number_input("연료 단가", value=1100 if energy_source=="면세유(경유)" else 50)
        target_temp = st.slider("목표 온도 (℃)", 10, 20, 15)
        
        insul_type = st.selectbox("보온 등급", 
                                  ["비닐 1겹 (U=5.5)", "비닐 2겹 (U=4.5)", "다겹보온커튼 (U=2.0)", "고효율 패키지 (U=1.5)"])
        u_values = {"비닐 1겹 (U=5.5)": 5.5, "비닐 2겹 (U=4.5)": 4.5, "다겹보온커튼 (U=2.0)": 2.0, "고효율 패키지 (U=1.5)": 1.5}
        u_val = u_values[insul_type]

    st.write("---")
    
    # 버튼
    run_btn = st.button("🚜 정밀 경영 분석 실행 (터치)", type="primary", use_container_width=True)

# --- 3. 핵심 알고리즘 (Engine) ---

def calculate_surface_area():
    roof_height = gh_ridge_h - gh_side_h
    roof_slope_len = math.sqrt((gh_width/2)**2 + roof_height**2)
    
    area_roof = 2 * roof_slope_len * gh_length * span_count 
    area_side = 2 * gh_length * gh_side_h 
    
    one_end_wall = (gh_width * gh_side_h) + (0.5 * gh_width * roof_height)
    area_end = one_end_wall * 2 * span_count 
    
    return area_roof + area_side + area_end

def calculate_depreciation():
    d1 = cost_film / 3       
    d2 = cost_curtain / 5    
    d3 = cost_heater / 10    
    d4 = cost_facility / 10  
    return (d1 + d2 + d3 + d4) * 10000 

def run_simulation(surface_area, region_info):
    """
    [지역별 기온 반영 시뮬레이션]
    region_info: 선택된 지역의 기후 데이터 {'base': 2.0, 'amp': 8.0}
    """
    dates = pd.date_range('2025-11-01', '2026-02-28') 
    
    total_rev = 0
    total_cost = 0
    
    eff = 0.85 if energy_source == "면세유(경유)" else 0.98
    calorific = 8500 if energy_source == "면세유(경유)" else 860
    
    daily_base_yield = winter_total_yield / 120
    
    base_t = region_info['base']
    amp_t = region_info['amp']

    for i, date in enumerate(dates):
        # ★ 지역별 기온 생성 로직 (10년 평년값 모사)
        # sin 함수로 겨울철 기온 하강 곡선 생성 + 지역별 편차 반영
        # 1월 중순(i=75)이 가장 춥도록 설정
        simulated_temp = base_t - (amp_t * np.sin(np.pi * i / 120)) 
        
        # 매일의 날씨 변동성(Randomness) 추가
        min_temp = simulated_temp + np.random.uniform(-2, 2)
        
        # 난방부하 계산
        delta_t = max(target_temp - min_temp, 0)
        daily_load = surface_area * u_val * delta_t * 14
        
        needed = daily_load / (calorific * eff)
        total_cost += needed * fuel_cost
        
        season_factor = 1.0
        if date.month == 1: season_factor = 0.8
        elif date.month == 11 or date.month == 2: season_factor = 1.1
            
        daily_yield = daily_base_yield * season_factor
        total_rev += daily_yield * market_price
        
    return int(total_rev), int(total_cost)

# --- 4. 결과 대시보드 ---

if run_btn:
    
    surface_area = calculate_surface_area()
    insul_ratio = surface_area / floor_area_m2
    
    # 선택된 지역의 기후 정보 가져오기
    selected_region_data = REGION_DATA[region_name]
    
    revenue, fuel_cost = run_simulation(surface_area, selected_region_data)
    depreciation = int(calculate_depreciation())
    
    net_profit = revenue - fuel_cost - depreciation
    
    # --- 결과 출력 ---
    st.subheader(f"📊 분석 리포트 ({region_name})")
    
    st.info(f"""
    **📍 지역 기후 분석**
    * **{region_name}**의 최근 10년 평년 기온 데이터를 적용했습니다.
    * 온실 표면적: {surface_area:.1f}㎡ (바닥 대비 {insul_ratio:.2f}배)
    """)
    
    c1, c2 = st.columns(2)
    c1.metric("예상 매출액", f"{revenue/10000:,.0f} 만원")
    c2.metric("총 비용 (난방+상각)", f"{(fuel_cost+depreciation)/10000:,.0f} 만원")
    
    st.metric("예상 순수익", f"{net_profit/10000:,.0f} 만원", 
              delta="흑자" if net_profit > 0 else "적자")

    st.write("---")
    
    st.subheader("💸 비용 상세")
    df_cost = pd.DataFrame({
        "항목": ["난방비", "감가상각비"],
        "금액": [fuel_cost, depreciation]
    })
    st.bar_chart(df_cost.set_index("항목"))
    
    st.markdown(f"""
    **💡 감가상각비 상세:**
    - 피복재: {int((cost_film/3)):,}만원
    - 보온커튼: {int((cost_curtain/5)):,}만원
    - 난방기: {int((cost_heater/10)):,}만원
    - 기타설비: {int((cost_facility/10)):,}만원
    """)
        
    st.subheader("⚖️ 의사결정 제언")
    
    if revenue > 0:
        margin = (net_profit / revenue) * 100
    else:
        margin = 0
    
    if net_profit > 0:
        st.success(f"""
        **✅ 겨울 재배 추천**
        * {region_name} 기후 조건에서 **{int(net_profit/10000):,}만원**의 이익이 예상됩니다.
        * 이익률: **{margin:.1f}%**
        """)
    else:
        st.error(f"""
        **❌ 재배 재고 필요**
        * {region_name} 지역은 겨울철 기온이 낮아 난방비 부담이 큽니다.
        * 적자 예상: **{int(abs(net_profit)/10000):,}만원**
        * 보온 커튼을 보강하거나 목표 수확량을 높여야 합니다.
        """)
            
else:
    st.info("👈 왼쪽 메뉴를 열어 데이터를 입력해주세요.")

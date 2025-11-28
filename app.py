import streamlit as st
import pandas as pd
import numpy as np
import math

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="무화과 정밀 경영 분석기 (Mobile)", layout="wide")

st.title("📱 [모바일용] 무화과 겨울재배 경영 분석")
st.markdown("왼쪽 상단 **화살표(>)**를 눌러 데이터를 입력하세요. 메뉴가 **접이식**으로 되어 있어 스마트폰에서 보기 편합니다.")
st.divider()

# --- 2. 사이드바: 데이터 입력 (접이식 적용) ---
with st.sidebar:
    st.header("📝 데이터 입력")
    st.info("아래 각 항목을 눌러서 입력창을 펼치세요.")

    # [1] 온실 규격 (기본적으로 펼쳐둠)
    with st.expander("1. 온실 규격 입력 (클릭)", expanded=True):
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
    with st.expander("2. 생산 목표 설정 (클릭)", expanded=False):
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
    with st.expander("3. 시설 투자 및 감가상각 (클릭)", expanded=False):
        cost_film = st.number_input("① 피복재 (3년)", value=200, step=50)
        cost_curtain = st.number_input("② 보온커튼 (5년)", value=1500, step=100)
        cost_heater = st.number_input("③ 난방기 (10년)", value=500, step=100)
        cost_facility = st.number_input("④ 기타 설비 (10년)", value=300, step=100)
        
        total_invest = cost_film + cost_curtain + cost_heater + cost_facility
        st.caption(f"💰 총 투자비: {total_invest:,} 만원")

    # [4] 에너지 설정
    with st.expander("4. 에너지 및 보온 (클릭)", expanded=False):
        energy_source = st.selectbox("사용 연료", ["면세유(경유)", "농사용 전기"])
        fuel_cost = st.number_input("연료 단가", value=1100 if energy_source=="면세유(경유)" else 50)
        target_temp = st.slider("목표 온도 (℃)", 10, 20, 15)
        
        insul_type = st.selectbox("보온 등급", 
                                  ["비닐 1겹 (U=5.5)", "비닐 2겹 (U=4.5)", "다겹보온커튼 (U=2.0)", "고효율 패키지 (U=1.5)"])
        u_values = {"비닐 1겹 (U=5.5)": 5.5, "비닐 2겹 (U=4.5)": 4.5, "다겹보온커튼 (U=2.0)": 2.0, "고효율 패키지 (U=1.5)": 1.5}
        u_val = u_values[insul_type]

    st.write("---")
    
    # 버튼을 사이드바 맨 아래에 큼지막하게 배치
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

def run_simulation(surface_area):
    dates = pd.date_range('2025-11-01', '2026-02-28') 
    
    total_rev = 0
    total_cost = 0
    
    eff = 0.85 if energy_source == "면세유(경유)" else 0.98
    calorific = 8500 if energy_source == "면세유(경유)" else 860
    
    daily_base_yield = winter_total_yield / 120
    
    for i, date in enumerate(dates):
        min_temp = 5 - (12 * np.sin(np.pi * i / 120)) + np.random.uniform(-1, 1)
        
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
    
    revenue, fuel_cost = run_simulation(surface_area)
    depreciation = int(calculate_depreciation())
    
    net_profit = revenue - fuel_cost - depreciation
    
    # --- 결과 출력 ---
    st.subheader("📊 분석 리포트")
    
    st.info(f"""
    **🏠 온실 구조 진단**
    * 바닥 면적: {floor_area_py:.1f}평
    * 표면적: {surface_area:.1f}㎡ (바닥 대비 {insul_ratio:.2f}배)
    * 여름 대비 목표: **{(winter_total_yield/summer_total_yield*100):.1f}%**
    """)
    
    # 모바일에서는 가로로 3개 배치가 좁을 수 있어서 2단/1단으로 변경
    c1, c2 = st.columns(2)
    c1.metric("예상 매출액", f"{revenue/10000:,.0f} 만원")
    c2.metric("총 비용", f"{(fuel_cost+depreciation)/10000:,.0f} 만원")
    
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
    **💡 감가상각비 상세 (1년 치):**
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
        * 순이익: **{int(net_profit/10000):,}만원**
        * 이익률: **{margin:.1f}%**
        """)
    else:
        st.error(f"""
        **❌ 재배 재고 필요**
        * 적자 예상: **{int(abs(net_profit)/10000):,}만원**
        """)
            
else:
    st.info("👈 왼쪽 상단 화살표(>)를 눌러 메뉴를 열고 데이터를 입력하세요.")

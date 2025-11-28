import streamlit as st
import pandas as pd
import numpy as np
import math

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="무화과 정밀 경영 분석기 (Pro)", layout="wide")

st.title("🏗️ 온실 규격 기반 무화과 겨울재배 정밀 진단")
st.markdown("""
평수만 입력하는 방식이 아닙니다. **온실의 폭, 길이, 높이, 연동 여부**를 입력하여
열이 빠져나가는 **'정확한 표면적'**을 산출하고 난방비를 예측합니다.
""")
st.divider()

# --- 2. 사이드바: 정밀 데이터 입력 ---
with st.sidebar:
    st.header("1. 온실 규격 (Geometry)")
    st.info("정확한 난방비 계산을 위해 온실 형태를 입력하세요.")
    
    gh_type = st.radio("온실 형태", ["단동 (1동)", "연동 (여러 동 연결)"])
    span_count = st.number_input("연동 수 (몇 동인가요?)", value=1 if gh_type=="단동 (1동)" else 3, step=1, min_value=1)
    
    c1, c2 = st.columns(2)
    gh_width = c1.number_input("폭 (m, 1동 기준)", value=6.0, step=0.5)
    gh_length = c2.number_input("길이 (m)", value=50.0, step=1.0)
    
    c3, c4 = st.columns(2)
    gh_side_h = c3.number_input("측고 (어깨높이 m)", value=2.0, step=0.2, help="땅에서 지붕 꺾이는 곳까지")
    gh_ridge_h = c4.number_input("동고 (중앙높이 m)", value=3.5, step=0.2, help="땅에서 지붕 제일 높은 곳까지")

    # 자동 계산된 바닥 면적 보여주기
    floor_area_m2 = gh_width * gh_length * span_count
    floor_area_py = floor_area_m2 / 3.3
    st.write(f"📐 계산된 바닥 면적: **{floor_area_py:.1f}평** ({floor_area_m2:.0f}㎡)")

    st.divider()

    st.header("2. 예상 수확량 (Yield)")
    base_yield = st.number_input("평소(여름) 총 수확량 (kg)", value=int(floor_area_py * 10), help="이 하우스에서 여름에 보통 따는 총 양을 적으세요.")
    yield_ratio = st.slider("여름 대비 겨울 생산성 (%)", 10, 100, 40, help="겨울은 일조량 부족으로 여름보다 수확량이 적습니다.")
    market_price = st.number_input("겨울철 예상 단가 (원/kg)", value=18000, step=1000)

    st.header("3. 시설 투자 및 감가상각")
    cost_total = st.number_input("총 시설 투자비 (만원)", value=1000, step=100)
    life_cycle = st.slider("평균 내용연수 (년)", 3, 15, 5, help="시설을 몇 년 쓸 수 있나요?")
    
    st.header("4. 에너지 및 보온")
    energy_source = st.selectbox("사용 연료", ["면세유(경유)", "농사용 전기"])
    fuel_cost = st.number_input("연료 단가", value=1100 if energy_source=="면세유(경유)" else 50)
    target_temp = st.slider("목표 온도 (℃)", 10, 20, 15)
    
    # U값 선택
    insul_type = st.selectbox("보온 자재 등급", 
                              ["비닐 1겹 (U=5.5)", "비닐 2겹 (U=4.5)", "다겹보온커튼 (U=2.0)", "고효율 패키지 (U=1.5)"])
    u_values = {"비닐 1겹 (U=5.5)": 5.5, "비닐 2겹 (U=4.5)": 4.5, "다겹보온커튼 (U=2.0)": 2.0, "고효율 패키지 (U=1.5)": 1.5}
    u_val = u_values[insul_type]

# --- 3. 표면적 및 난방부하 계산 로직 (Physics Engine) ---

def calculate_surface_area():
    """
    [핵심 알고리즘] 온실의 기하학적 표면적(Surface Area) 계산
    단동 vs 연동에 따라 외기에 접하는 면적이 달라짐
    """
    # 1. 지붕 면적 (피타고라스 정리 이용)
    # 지붕 빗변 길이
    roof_height = gh_ridge_h - gh_side_h
    roof_slope_len = math.sqrt((gh_width/2)**2 + roof_height**2)
    # 지붕 전체 면적 (양쪽 * 길이 * 동수)
    area_roof = 2 * roof_slope_len * gh_length * span_count
    
    # 2. 측면 벽 면적 (Side Walls)
    # 연동일 경우, 맞닿은 벽은 외기에 접하지 않으므로 계산에서 제외해야 함
    # 외기에 접하는 측면은 항상 양 끝 2개면 뿐임 (길이 방향)
    area_side = 2 * gh_length * gh_side_h
    
    # 3. 앞/뒤 마구리 면적 (End Walls)
    # (직사각형 부분 + 삼각형 지붕 부분) * (앞+뒤) * 동수
    one_end_wall = (gh_width * gh_side_h) + (0.5 * gh_width * roof_height)
    area_end = one_end_wall * 2 * span_count
    
    total_surface_area = area_roof + area_side + area_end
    return total_surface_area

def run_simulation(surface_area):
    dates = pd.date_range('2025-11-01', '2026-02-28')
    
    total_rev = 0
    total_cost = 0
    
    eff = 0.85 if energy_source == "면세유(경유)" else 0.98
    calorific = 8500 if energy_source == "면세유(경유)" else 860
    
    for i, date in enumerate(dates):
        # 기온 시뮬레이션
        min_temp = 5 - (12 * np.sin(np.pi * i / 120)) + np.random.uniform(-1, 1)
        
        # 난방부하 = 표면적 * U값 * 온도차 * 시간
        delta_t = max(target_temp - min_temp, 0)
        # 중요: 표면적(surface_area)을 사용함!
        daily_load = surface_area * u_val * delta_t * 14 
        
        # 비용 계산
        needed = daily_load / (calorific * eff)
        total_cost += needed * fuel_cost
        
        # 수확량 계산
        # 사용자가 입력한 '평소 수확량'을 120일로 나누고, 겨울철 감수율 적용
        daily_yield = (base_yield / 120) * (yield_ratio / 100)
        
        # 혹한기 추가 감수 로직
        if 12 <= date.month <= 1: daily_yield *= 0.8
        
        total_rev += daily_yield * market_price
        
    return int(total_rev), int(total_cost)

# --- 4. 결과 화면 ---

if st.button("🏗️ 정밀 분석 실행"):
    
    # 1. 표면적 계산
    surface_area = calculate_surface_area()
    # 보온비(표면적 / 바닥면적): 낮을수록 에너지 효율 좋음
    insul_ratio = surface_area / floor_area_m2
    
    # 2. 시뮬레이션
    rev, fuel_cost = run_simulation(surface_area)
    
    # 3. 감가상각비 (연간)
    depreciation = (cost_total * 10000) / life_cycle
    
    # 4. 순수익
    net_profit = rev - fuel_cost - depreciation
    
    # --- 결과 표시 ---
    st.subheader("📊 분석 결과")
    
    # 온실 구조 진단
    st.info(f"""
    **🏠 온실 구조 진단 결과**
    * 바닥 면적: {floor_area_m2:.1f}㎡ ({floor_area_py:.1f}평)
    * **열 손실 표면적: {surface_area:.1f}㎡** (바닥 대비 {insul_ratio:.2f}배)
    * {'✅ 연동형이라 단동 대비 에너지 효율이 좋습니다.' if span_count > 1 else '⚠️ 단동형이라 표면적이 넓어 난방비가 많이 듭니다.'}
    """)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("예상 겨울 매출", f"{rev/10000:,.0f} 만원")
    c2.metric("총 비용 (연료+상각)", f"{(fuel_cost+depreciation)/10000:,.0f} 만원")
    c3.metric("예상 순수익", f"{net_profit/10000:,.0f} 만원", delta="흑자" if net_profit>0 else "적자")
    
    # 비용 상세 차트
    st.write("---")
    st.subheader("💸 비용 vs 수익 구조")
    
    df = pd.DataFrame({
        "항목": ["매출액", "난방비", "감가상각비", "순수익"],
        "금액": [rev, fuel_cost, depreciation, net_profit]
    })
    st.bar_chart(df.set_index("항목"))
    
    if net_profit > 0:
        st.success("겨울 재배 시 수익성이 있습니다!")
    else:
        st.error("현재 조건에서는 적자가 예상됩니다. 보온력을 높이거나 단가를 더 받아야 합니다.")

else:
    st.write("👈 왼쪽에서 온실 규격과 데이터를 입력하고 버튼을 눌러주세요.")

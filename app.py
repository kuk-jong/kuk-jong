import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="무화과 정밀 경영 분석기", layout="wide")

st.title("🏭 무화과 겨울재배 시설투자 감가상각 및 수익성 분석")
st.markdown("""
시설 자재별 **내용연수(수명)**를 고려한 정밀 경제성 분석 모델입니다. 
단순한 현금 흐름이 아닌, **감가상각비를 반영한 실질 순수익**을 예측합니다.
""")
st.divider()

# --- 2. 사이드바: 데이터 입력 ---
with st.sidebar:
    st.header("1. 기본 재배 환경")
    area_py = st.number_input("재배 면적 (평)", value=500, step=50)
    target_temp = st.slider("겨울철 목표 온도 (℃)", 10, 20, 15)
    
    st.header("2. 겨울철 시장 예측")
    market_price = st.number_input("예상 도매가 (원/kg)", value=18000, step=1000)
    yield_efficiency = st.slider("여름 대비 겨울 생산성 (%)", 10, 100, 40, help="겨울은 일조량 부족으로 수량이 적습니다.")

    st.divider()
    
    st.header("3. 시설 투자 및 자재비 (만원)")
    st.info("겨울 재배를 위해 투입되는 자재비를 입력하세요.")
    
    # 자재별 입력 (내용연수 적용)
    cost_film = st.number_input("① 피복재 (PE필름 등)", value=200, help="내용연수 3년 적용")
    cost_curtain = st.number_input("② 보온커튼 (다겹 등)", value=1500, help="내용연수 5년 적용")
    cost_heater = st.number_input("③ 난방기 (온풍기 등)", value=500, help="내용연수 10년 적용")
    cost_facility = st.number_input("④ 기타 설비 (관수 등)", value=300, help="내용연수 10년 적용")

    st.header("4. 에너지 비용")
    energy_type = st.radio("사용 연료", ["면세유(경유)", "농사용 전기"])
    fuel_price = st.number_input("연료 단가 (원)", value=1100 if energy_type=="면세유(경유)" else 50)
    
    # 시설 상태에 따른 U값 선택 (보온커튼 투자 여부에 따라 자동 보정 추천)
    st.write("---")
    st.write("**[시설 단열 수준 선택]**")
    if cost_curtain > 0:
        def_idx = 2 # 커튼 돈 썼으면 '좋음' 기본값
    else:
        def_idx = 0 # 커튼 돈 안 썼으면 '나쁨' 기본값
        
    insulation_level = st.selectbox(
        "현재 시설의 보온 성능",
        ["하 (비닐 1~2겹)", "중 (비닐+부직포)", "상 (다겹보온커튼)", "최상 (알루미늄스크린)"],
        index=def_idx
    )

# --- 3. 내부 연산 로직 (Engine) ---

# 단열 성능(U값) 매핑
u_val_map = {"하 (비닐 1~2겹)": 4.5, "중 (비닐+부직포)": 3.0, "상 (다겹보온커튼)": 2.0, "최상 (알루미늄스크린)": 1.5}
u_value = u_val_map[insulation_level]

def calculate_depreciation():
    """
    연간 감가상각비 계산 함수 (정액법)
    """
    dep_film = cost_film / 3       # 3년
    dep_curtain = cost_curtain / 5 # 5년
    dep_heater = cost_heater / 10  # 10년
    dep_facility = cost_facility / 10 # 10년
    
    total_dep = dep_film + dep_curtain + dep_heater + dep_facility
    return total_dep * 10000 # 만원 단위 -> 원 단위 변환

def run_simulation():
    """
    겨울 작기(11월~2월) 시뮬레이션
    """
    area_m2 = area_py * 3.3
    dates = pd.date_range('2025-11-01', '2026-02-28')
    
    total_revenue = 0
    total_fuel_cost = 0
    
    # 에너지 효율 설정
    eff = 0.85 if energy_type == "면세유(경유)" else 0.98
    calorific = 8500 if energy_type == "면세유(경유)" else 860
    
    for i, date in enumerate(dates):
        # 1. 기온 시뮬레이션
        min_temp = 5 - (12 * np.sin(np.pi * i / 120)) + np.random.uniform(-1.5, 1.5)
        
        # 2. 난방부하 계산
        delta_t = max(target_temp - min_temp, 0)
        heat_load = area_m2 * u_value * delta_t * 14 # 야간 14시간
        
        # 3. 연료비 계산
        fuel_needed = heat_load / (calorific * eff)
        daily_cost = fuel_needed * fuel_price
        total_fuel_cost += daily_cost
        
        # 4. 매출 계산 (생산성 효율 적용)
        std_yield = 30 * (area_m2 / 1000) 
        daily_yield = std_yield * (yield_efficiency / 100)
        
        # 혹한기(12~1월) 생산량 추가 감소 로직
        if 11 <= date.month <= 1: daily_yield *= 0.85
            
        total_revenue += daily_yield * market_price

    return int(total_revenue), int(total_fuel_cost)


# --- 4. 결과 시각화 (Dashboard) ---

if st.button("📊 정밀 경제성 분석 실행"):
    
    # 계산 실행
    annual_revenue, annual_fuel_cost = run_simulation()
    annual_depreciation = int(calculate_depreciation())
    
    # 총 비용 및 순수익
    total_annual_cost = annual_fuel_cost + annual_depreciation
    net_profit = annual_revenue - total_annual_cost
    
    # --- [화면 구성] ---
    
    # 1. 핵심 지표 (KPI)
    st.subheader("📢 분석 결과 요약 (1년 기준)")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("예상 매출액", f"{annual_revenue/10000:,.0f} 만원")
    c2.metric("총 비용 (난방+상각)", f"{total_annual_cost/10000:,.0f} 만원")
    c3.metric("실질 순수익", f"{net_profit/10000:,.0f} 만원", 
              delta="흑자" if net_profit > 0 else "적자", delta_color="normal")
    
    # 손익분기점(BEP) 판정
    roi_percent = (net_profit / (annual_revenue + 1)) * 100 # 매출액 순이익률
    c4.metric("매출액 순이익률", f"{roi_percent:.1f} %")

    st.divider()

    # 2. 비용 구조 분석 (Chart)
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("💸 연간 비용 상세 구조")
        st.caption("내가 번 돈이 어디로 나가는지 확인하세요.")
        
        cost_df = pd.DataFrame({
            '비용 항목': ['난방비 (변동비)', '감가상각비 (고정비)'],
            '금액': [annual_fuel_cost, annual_depreciation]
        })
        st.bar_chart(cost_df.set_index('비용 항목'))
        
        st.info(f"""
        **💡 감가상각비 상세 (매년 비축해야 할 돈):**
        * 피복재(3년): {int(cost_film/3):,}만원
        * 보온커튼(5년): {int(cost_curtain/5):,}만원
        * 난방기(10년): {int(cost_heater/10):,}만원
        * 기타설비(10년): {int(cost_facility/10):,}만원
        **합계: 연 {int(annual_depreciation/10000):,}만원**
        """)

    with col_chart2:
        st.subheader("⚖️ 최종 의사결정 제언")
        
        if net_profit > 5000000: # 순이익 500만원 이상
            st.success(f"""
            ✅ **[적극 추천] 고수익 구간입니다!**
            * 시설 투자비와 난방비를 모두 제하고도 **연간 약 {int(net_profit/10000):,}만원**의 순수익이 남습니다.
            * 감가상각비를 고려해도 충분히 경제성이 있습니다.
            """)
        elif net_profit > 0:
            st.warning(f"""
            ⚠️ **[신중 검토] 수익이 나지만 크지 않습니다.**
            * 연간 순수익이 **{int(net_profit/10000):,}만원** 수준입니다.
            * 인건비나 돌발 상황을 고려하면 적자로 돌아설 위험이 있습니다.
            * 겨울철 생산성을 높이거나 난방비를 더 줄일 방법을 찾아보세요.
            """)
        else:
            st.error(f"""
            ❌ **[투자 불가] 하면 손해입니다.**
            * 매년 **{int(abs(net_profit)/10000):,}만원씩 손해**를 보게 됩니다.
            * 매출보다 배보다 배꼽(난방비+상각비)이 더 큽니다.
            * 투자를 포기하거나, 고효율 난방 시설을 먼저 확보해야 합니다.
            """)

else:
    st.info("👈 왼쪽 사이드바에서 시설 투자비와 재배 정보를 입력하세요.")

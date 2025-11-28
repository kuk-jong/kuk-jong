import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="무화과 겨울재배 투자 분석기", layout="wide")

st.title("🏭 무화과 겨울재배 시설투자 타당성 분석 시스템")
st.markdown("현재 시설로 겨울 농사를 지을 때와, **시설 투자를 했을 때의 수익성을 비교**하여 의사결정을 도와드립니다.")
st.divider()

# --- 2. 사이드바: 데이터 입력 ---
with st.sidebar:
    st.header("1. 농장 기본 정보")
    area_py = st.number_input("재배 면적 (평)", value=500, step=50)
    target_temp = st.slider("목표 유지 온도 (℃)", 10, 20, 15)
    
    st.header("2. 겨울철 시장 예측")
    market_price = st.number_input("예상 도매가 (원/kg)", value=20000, step=1000, help="겨울철 높은 단가를 입력하세요")
    yield_efficiency = st.slider("여름 대비 겨울 생산성 (%)", 10, 100, 40, help="겨울은 일조량 부족으로 수량이 적습니다.")

    st.header("3. 시설 투자 시나리오")
    st.info("현재 상태와 바꾸고 싶은 시설을 선택하세요.")
    
    # 시설 등급별 U값(열관류율) 정의 (낮을수록 좋음)
    insulation_options = {
        "비닐 1겹 (단열 매우 나쁨)": 5.5,
        "비닐 2겹 (단열 보통)": 3.5,
        "다겹보온커튼 5겹 (단열 좋음)": 2.0,
        "다겹보온커튼 7겹+알루미늄 (단열 최상)": 1.2
    }
    
    current_facility = st.selectbox("현재 내 하우스 상태", list(insulation_options.keys()), index=0)
    future_facility = st.selectbox("투자 후 시설 상태 (목표)", list(insulation_options.keys()), index=2)
    
    investment_cost = st.number_input("예상 시설 투자비 (만원)", value=1500, step=100) * 10000 # 원 단위 변환

    st.header("4. 에너지 비용")
    energy_type = st.radio("사용 연료", ["면세유(경유)", "농사용 전기"])
    fuel_price = st.number_input("연료 단가 (원)", value=1100 if energy_type=="면세유(경유)" else 50)


# --- 3. 분석 로직 (Engine) ---

def calculate_season(u_value):
    """
    겨울 작기(11월~2월, 120일) 시뮬레이션
    """
    area_m2 = area_py * 3.3
    dates = pd.date_range('2025-11-01', '2026-02-28')
    
    total_revenue = 0
    total_fuel_cost = 0
    
    # 에너지 효율
    eff = 0.85 if energy_type == "면세유(경유)" else 0.98
    calorific = 8500 if energy_type == "면세유(경유)" else 860 # kcal 기준
    
    for i, date in enumerate(dates):
        # 1. 기온 시뮬레이션 (1월이 가장 춥게)
        min_temp = 5 - (10 * np.sin(np.pi * i / 120)) + np.random.uniform(-2, 2)
        
        # 2. 난방부하 계산 (Q = A * U * dT * Time)
        delta_t = max(target_temp - min_temp, 0)
        heat_load = area_m2 * u_value * delta_t * 14 # 야간 14시간 가동 가정
        
        # 3. 연료비 계산
        fuel_needed = heat_load / (calorific * eff)
        daily_cost = fuel_needed * fuel_price
        total_fuel_cost += daily_cost
        
        # 4. 생산량 및 매출 계산
        # 여름 평균(30kg/10a 가정) * 면적비율 * 겨울생산성효율
        std_yield = 30 * (area_m2 / 1000) 
        daily_yield = std_yield * (yield_efficiency / 100)
        
        # 12월~1월은 수량이 더 떨어진다고 가정 (일조량 최저)
        if 11 <= date.month <= 1: 
            daily_yield *= 0.8
            
        total_revenue += daily_yield * market_price

    return int(total_revenue), int(total_fuel_cost)


# --- 4. 결과 시각화 (Dashboard) ---

if st.button("💰 투자 분석 결과 보기"):
    
    # 1. 시뮬레이션 실행
    cur_u = insulation_options[current_facility]
    fut_u = insulation_options[future_facility]
    
    rev_cur, cost_cur = calculate_season(cur_u)
    rev_fut, cost_fut = calculate_season(fut_u)
    
    profit_cur = rev_cur - cost_cur
    profit_fut = rev_fut - cost_fut
    
    fuel_saving = cost_cur - cost_fut # 절감된 난방비
    increased_profit = profit_fut - profit_cur # 늘어난 이익
    
    # 2. 투자 회수 기간 계산
    if increased_profit > 0:
        payback_years = investment_cost / increased_profit
    else:
        payback_years = 999 # 회수 불가능

    # --- 화면 구성 ---
    
    # 상단 요약 배너
    st.subheader("📊 분석 요약")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="현재 시설 순수익(1년)", 
            value=f"{profit_cur/10000:,.0f} 만원",
            delta="겨울재배 시"
        )
    with col2:
        st.metric(
            label="투자 후 순수익(1년)", 
            value=f"{profit_fut/10000:,.0f} 만원",
            delta=f"+{(profit_fut-profit_cur)/10000:,.0f} 만원 증가"
        )
    with col3:
        if payback_years < 10:
            st.metric(
                label="투자비 회수 기간", 
                value=f"{payback_years:.1f} 년",
                delta="이후 순수익 전환"
            )
        else:
            st.error("투자 회수 불가능 (수익 증가분이 적음)")

    st.divider()

    # 상세 분석
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🔥 난방비 절감 효과")
        st.write(f"시설 투자 시, 연간 난방비가 **{cost_cur/10000:,.0f}만원**에서 **{cost_fut/10000:,.0f}만원**으로 줄어듭니다.")
        
        # 바 차트
        df_cost = pd.DataFrame({
            '구분': ['현재 시설', '투자 후 시설'],
            '난방비': [cost_cur, cost_fut]
        })
        st.bar_chart(df_cost.set_index('구분'))

    with c2:
        st.subheader("⚖️ 투자 타당성 판정")
        if profit_cur < 0:
            st.warning("⚠️ **현재 시설로는 겨울 재배 시 적자**가 발생합니다. 투자가 필수적입니다.")
        
        if payback_years <= 2:
            st.success(f"✅ **적극 추천:** 투자비를 **{payback_years:.1f}년** 만에 뽑을 수 있는 아주 좋은 투자입니다.")
        elif payback_years <= 5:
            st.info(f"☑️ **보통:** 투자 회수에 **{payback_years:.1f}년**이 걸립니다. 장기적으로 보고 결정하세요.")
        else:
            st.error("❌ **비추천:** 투자비 회수에 너무 오랜 시간이 걸립니다. 난방 효율을 더 높이거나 투자비를 줄이세요.")

    # 5년치 현금흐름표
    st.subheader("📅 향후 5년간 예상 현금 흐름 (ROI)")
    years = [1, 2, 3, 4, 5]
    cash_flow = [-investment_cost + (profit_fut * y) for y in years] # 누적 순이익 - 투자비
    
    df_roi = pd.DataFrame({
        '년차': [f"{y}년차" for y in years],
        '누적 손익': cash_flow
    })
    
    st.line_chart(df_roi.set_index('년차'))
    st.caption("* 그래프가 0 위로 올라가는 시점이 손익분기점입니다.")

else:
    st.info("👈 왼쪽에서 농가 정보와 투자 계획을 입력하고 버튼을 눌러주세요.")

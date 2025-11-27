import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="무화과 소득 최적화 도우미", layout="wide")

st.title("🍇 무화과 겨울재배 경영 의사결정 지원 시스템")
st.markdown("""
**내 하우스 환경과 현재 에너지 가격을 입력하세요.** 빅데이터 분석을 통해 **최적의 수확 종료일**과 **예상 수익**을 알려드립니다.
""")
st.divider()

# --- 2. 사이드바: 농가 입력창 (User Inputs) ---
st.sidebar.header("📝 농가 환경 입력")

# 2-1. 하우스 정보
area_py = st.sidebar.number_input("재배 면적 (평)", value=300, step=50)
insulation = st.sidebar.selectbox(
    "보온 자재 상태", 
    ["1등급 (다겹보온커튼 7겹 이상)", "2등급 (다겹보온커튼 5겹)", "3등급 (일반 비닐+부직포)"],
    index=1
)

# 2-2. 난방 정보
heat_type = st.sidebar.radio("난방기 종류", ["경유 온풍기", "전기 난방기"])
target_temp = st.sidebar.slider("목표 유지 온도 (℃)", 10, 20, 15)

# 2-3. 비용 정보
st.sidebar.subheader("💰 현재 시세 입력")
oil_price = st.sidebar.number_input("면세유 가격 (원/L)", value=1100, step=10)
elec_price = st.sidebar.number_input("농사용 전기료 (원/kWh)", value=55, step=1)
market_price = st.sidebar.number_input("무화과 예상 도매가 (원/kg)", value=18000, step=1000)

# --- 3. 내부 연산 로직 (Calculation Engine) ---

# 보온 등급에 따른 열관류율(U값) 매핑
u_val_map = {
    "1등급 (다겹보온커튼 7겹 이상)": 1.5,
    "2등급 (다겹보온커튼 5겹)": 2.5,
    "3등급 (일반 비닐+부직포)": 4.0
}
u_value = u_val_map[insulation]

# 효율 설정
eff_oil = 0.85
eff_elec = 0.98

# 데이터 생성 함수
def run_simulation():
    # 11월 1일 ~ 2월 28일 날짜 생성
    dates = pd.date_range(start='2025-11-01', end='2026-02-28')
    data = []
    
    cumulative_profit = 0
    area_m2 = area_py * 3.3
    
    for i, date in enumerate(dates):
        # 가상의 기온 데이터 (1월 중순 최저)
        temp_min = 8 - (12 * np.sin(np.pi * i / 120)) + np.random.uniform(-1, 1)
        
        # 난방부하 계산
        delta_t = max(target_temp - temp_min, 0)
        heat_load = area_m2 * u_value * delta_t * 14 # 야간 14시간
        
        # 비용 계산
        cost = 0
        if heat_type == "경유 온풍기":
            liters = heat_load / (8500 * eff_oil)
            cost = liters * oil_price
        else:
            kwh = heat_load / (860 * eff_elec)
            cost = kwh * elec_price
            
        # 수익 계산 (날짜가 갈수록 수확량 조금씩 감소 가정)
        yield_kg = (30 * (area_m2/1000)) * (1 - i*0.003) 
        if yield_kg < 0: yield_kg = 0
        revenue = yield_kg * market_price
        
        # 순이익
        daily_profit = revenue - cost
        cumulative_profit += daily_profit
        
        data.append([date, int(cost), int(revenue), int(daily_profit), int(cumulative_profit)])
        
    return pd.DataFrame(data, columns=['날짜', '난방비', '매출액', '일일순익', '누적순익'])

# --- 4. 결과 출력 화면 (Dashboard) ---

if st.sidebar.button("결과 분석하기 (Click)"):
    df = run_simulation()
    
    # 최적점 찾기 (누적순익이 최대인 날)
    max_idx = df['누적순익'].idxmax()
    best_date = df.loc[max_idx, '날짜']
    max_profit = df.loc[max_idx, '누적순익']
    
    # 4-1. 핵심 메시지 (Metric)
    st.success(f"📢 분석 결과, 사장님 농장의 최적 수확 종료일은 **{best_date.strftime('%Y년 %m월 %d일')}** 입니다.")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("예상 최대 순수익", f"{max_profit:,.0f} 원")
    col2.metric("이때까지 예상 매출", f"{df.loc[max_idx, '매출액']:,.0f} 원")
    col3.metric("예상 난방비 총액", f"{df.loc[:max_idx, '난방비'].sum():,.0f} 원")

    # 4-2. 상세 조언
    st.info(f"""
    💡 **경영 조언:**
    * **{best_date.strftime('%m월 %d일')}** 이후에는 난방비가 수확 수익보다 커지는 '적자 구간'에 진입합니다.
    * 현재 **{heat_type}**를 사용 중이시며, 목표온도 **{target_temp}℃** 유지 시 분석된 결과입니다.
    """)

    # 4-3. 그래프 시각화
    st.subheader("📈 일별 수익 vs 난방비 변화 추이")
    
    # 차트용 데이터 가공
    chart_data = df.set_index('날짜')[['매출액', '난방비']]
    st.line_chart(chart_data)
    
    st.subheader("💰 누적 순이익 곡선 (언제 꺾이는가?)")
    st.line_chart(df.set_index('날짜')['누적순익'])

    # 4-4. 데이터 표
    with st.expander("📊 상세 데이터 표 보기"):
        st.dataframe(df)

else:
    st.info("👈 왼쪽 사이드바에서 농가 정보를 입력하고 '결과 분석하기' 버튼을 눌러주세요.")
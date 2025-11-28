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
    [지역

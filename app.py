import streamlit as st
import pandas as pd
import numpy as np
import math

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="무화과 정밀 경영 분석기 (Final)", layout="wide")

st.title("🏗️ 온실 규격 및 자재별 감가상각 반영 경영 분석")
st.markdown("""
**온실의 기하학적 구조(표면적)**와 **자재별 내용연수**를 모두 고려한 완성형 모델입니다.
농가가 예상하는 **겨울철 총 생산량**을 직접 입력하여 시뮬레이션합니다.
""")
st.divider()

# --- 2. 사이드바: 데이터 입력 ---
with st.sidebar:
    st.header("1. 온실 규격 (Geometry)")
    st.info("정확한 난방비 계산을 위해 온실 형태를 입력하세요.")
    
    gh_type = st.radio("온실 형태", ["단동 (1동)", "연동 (여러 동 연결)"])
    span_count = st.number_input("연동 수 (몇 동인가요?)", value=1 if gh_type=="단동 (1동)" else 3, step=1, min_value=1)
    
    c1, c2 = st.columns(2)
    gh_width = c1.number_input("폭 (m, 1동 기준)", value=6.0, step=0.5)
    gh_length = c2.number_input("길이 (m)", value=50.0, step=1.0)
    
    c3, c4 = st.columns(2)
    gh_side_h = c3.number_input("측고 (어깨높이 m)", value=2.0, step=0.2)
    gh_ridge_h = c4.number_input("동고 (중앙높이 m)", value=3.5, step=0.2)

    # 바닥 면적 자동 계산
    floor_area_m2 = gh_width * gh_length * span_count
    floor_area_py = floor_area_m2 / 3.3
    st.write(f"📐 바닥 면적: **{floor_area_py:.1f}평** ({floor_area_m2:.0f}㎡)")

    st.divider()

    st.header("2. 겨울철 생산 목표")
    # 수정: 비율(%) 대신 직접 입력으로 변경
    winter_total_yield = st.number_input(
        "겨울 작기 예상 총 생산량 (kg)", 
        value=int(floor_area_py * 10), 
        step=100,
        help="11월~2월 동안 수확할 것으로 예상되는 총 무게를 입력하세요."
    )
    market_price = st.number_input("겨울철 예상 단가 (원/kg)", value=18000, step=1000)

    st.divider()

    st.header("3. 시설 투자 및 감가상각")
    st.info("내용연수가 다른 자재들을 구분하여 입력하세요.")
    
    # 수정: 자재별 상세 입력 부활
    cost_film = st.number_input("① 피복재 (PE필름 등, 3년)", value=200, step=50)
    cost_curtain = st.number_input("② 보온커튼 (다겹 등, 5년)", value=1500, step=100)
    cost_heater = st.number_input("③ 난방기 (온풍기 등, 10년)", value=500, step=100)
    cost_facility = st.number_input("④ 기타 설비 (관수 등, 10년)", value=300, step=100)
    
    # 총 투자비 자동 합산 표시
    total_invest = cost_film + cost_curtain + cost_heater + cost_facility
    st.caption(f"💰 총 시설 투자비: {total_invest:,} 만원")

    st.divider()

    st.header("4. 에너지 및 보온")
    energy_source = st.selectbox("사용 연료", ["면세유(경유)", "농사용 전기"])
    fuel_cost = st.number_input("연료 단가", value=1100 if energy_source=="면세유(경유)" else 50)
    target_temp = st.slider("목표 온도 (℃)", 10, 20, 15)
    
    insul_type = st.selectbox("보온 자재 등급", 
                              ["비닐 1겹 (U=5.5)", "비닐 2겹 (U=4.5)", "다겹보온커튼 (U=2.0)", "고효율 패키지 (U=1.5)"])
    u_values = {"비닐 1겹 (U=5.5)": 5.5, "비닐 2겹 (U=4.5)": 4.5, "다겹보온커튼 (U=2.0)": 2.0, "고효율 패키지 (U=1.5)": 1.5}
    u_val = u_values[insul_type]

# --- 3. 핵심 알고리즘 (Engine) ---

def calculate_surface_area():
    """
    온실 표면적 계산 (단동/연동 반영)
    """
    roof_height = gh_ridge_h - gh_side_h
    roof_slope_len = math.sqrt((gh_width/2)**2 + roof_height**2)
    
    area_roof = 2 * roof_slope_len * gh_length * span_count # 지붕
    area_side = 2 * gh_length * gh_side_h # 측벽 (양 끝 2면만 외기 접촉)
    
    one_end_wall = (gh_width * gh_side_h) + (0.5 * gh_width * roof_height)
    area_end = one_end_wall * 2 * span_count # 앞뒤 마구리
    
    return area_roof + area_side + area_end

def calculate_depreciation():
    """
    자재별 내용연수를 반영한 연간 감가상각비 총액 계산
    """
    d1 = cost_film / 3       # 3년
    d2 = cost_curtain / 5    # 5년
    d3 = cost_heater / 10    # 10년
    d4 = cost_facility / 10  # 10년
    
    return (d1 + d2 + d3 + d4) * 10000 # 원 단위 반환

def run_simulation(surface_area):
    dates = pd.date_range('2025-11-01', '2026-02-28') # 120일
    
    total_rev = 0
    total_cost = 0
    
    eff = 0.85 if energy_source == "면세유(경유)" else 0.98
    calorific = 8500 if energy_source == "면세유(경유)" else 860

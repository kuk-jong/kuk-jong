import streamlit as st
import pandas as pd
import numpy as np
import math

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="무화과 정밀 경영 분석기 (Final)", layout="wide")

st.title("🏗️ 온실 규격 및 자재별 감가상각 반영 경영 분석")
st.markdown("""
**온실의 기하학적 구조(표면적)**와 **자재별 내용연수**를 모두 고려한 완성형 모델입니다.
왼쪽 사이드바에서 데이터를 입력하고 **맨 아래 버튼**을 눌러주세요.
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

    st.header("2. 생산 목표 설정")
    
    # [추가됨] 여름철 생산량 입력칸
    summer_total_yield = st.number_input(
        "🌞 평소(여름) 총 생산량 (kg)", 
        value=int(floor_area_py * 10), 
        step=100,
        help="이 하우스에서 여름 작기에 보통 수확하는 총량을 입력하세요."
    )
    
    # 겨울철

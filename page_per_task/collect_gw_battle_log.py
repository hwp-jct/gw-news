import os
import sys
from datetime import datetime
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils as ut
import game_log_collector as glc

if not ut.st_check_password():
    st.stop()

st.subheader("DB로 부터 배틀 로그 수집")
st.markdown("""
1. DB로 부터 세계 대전 정보 수집
    - 참여 서버 정보 목록
    - 대진표 정보 목록
    - 전투 로그 정보 목록
    - 서버별 통계 정보
    - 제독별 통계 정보
2. S3에서 로그 파일 다운로드
    - 서버별 게임 로그 파일 다운로드
    - 로그 파일 압축 해제
    - Reason 30004, 30005, 30027 로그 추출
""")


today = pd.Timestamp.today()
yesterday = today - pd.Timedelta(days=1)
st.sidebar.date_input("시작일", value=yesterday)
st.sidebar.time_input("시작시간", value=yesterday)
st.sidebar.date_input("종료일", value=today)
st.sidebar.time_input("종료시간", value=today)


if st.button("로그 수집 시작"):
    server_ids = ['1029']
    glc.s3_fetch_game_log_process(server_ids, datetime(2024, 6, 1), datetime(2024, 6, 1))

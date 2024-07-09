import os
import sys
from datetime import datetime
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils as ut
import collect_log as collector

if not ut.st_check_password():
    st.stop()

st_ss = st.session_state

st.subheader("로그 수집")
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

st.divider()

# yesterday = today - pd.Timedelta(days=1)
# today = pd.Timestamp.today()
yesterday = datetime(2024, 6, 1, 10)
today = yesterday + pd.Timedelta(days=1)

sc1, sc2 = st.columns([1, 1])
sc1.date_input("시작일", value=yesterday)
sc2.time_input("시작시간", value=yesterday)
ec1, ec2 = st.columns([1, 1])
ec1.date_input("종료일", value=today)
ec2.time_input("종료시간", value=today)

st.info('테스트를 위해 특정 서버(1133, 2092)의 로그만 수집합니다.')


if st_ss.get("btn_collect", False):
    server_ids = [1133, 2092]
    collector.s3_fetch_game_log_process(server_ids, yesterday, today)
st.button("로그 수집 시작", key="btn_collect")

# def st_on_btn_collect():
#     server_ids = [1133, 2092]
#     with ut.dont_disturb():
#         collector.s3_fetch_game_log_process(server_ids, yesterday, today)
# st.button("로그 수집 시작", key="btn_collect", on_click=st_on_btn_collect, disabled=ut.DONT_DISTURB)

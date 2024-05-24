import os
import sys
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils as ut
# import main_bl_scrap as mbs
import main_bl_analyzer as bla

if not ut.check_password():
    st.stop()

st.subheader("DB로 부터 배틀 로그 수집")
st.write("DB로 부터 배틀 로그와 관련된 데이터를 수집합니다.")
st.write("배틀로그의 ID를 이름으로 변경하기 위해 User와 Guild의 이름 목록도 필요합니다.")
st.write("라이브 서버의 DB에서 데이터를 가져오면 서비스에 영향을 줄 수 있기 때문에 분할해서 수집하거나 별도의 백업 DB에서 수집하는 것이 좋습니다.")
st.write("아직 어떤 방식이 좋을지 결정되지 않아 구현은 하지 않았습니다.")
st.write("월드 뉴스에 사용할 데이터는 라이브 서버의 4월 4일자 로그의 일부를 사용했습니다")


st.subheader("배틀로그 데이터 샘플")
with st.spinner("Loading data..."):
    # not yet implemented
    # view sample csv file
    if os.path.exists(ut.get_work_path("fromdb/bl-20240404-0000.csv")):
        df = ut.pd_read_csv(ut.get_work_path("fromdb/bl-20240404-0000.csv"))
        df.columns = bla.get_battle_log_headers(True)
        st.write(df.head())

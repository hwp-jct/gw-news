import os
import sys
import pandas as pd
import streamlit as st
from stqdm import stqdm

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils as ut
import main_bl_analyzer as bla


if not ut.check_password():
    st.stop()

# cwd = os.path.dirname(os.path.abspath(__file__))
# os.chdir(cwd)

st.subheader("연합간 전투 로그 분석")

if not st.button("Start analyzing battle logs"):
    st.stop()

with st.status("Analyzing battle logs...", expanded=True) as status:
    st.write("Merging battle logs...")
    # merged_df = bla.merge_battle_logs() # 함수 그대로 복사해서 실행
    data_folder = ut.get_work_path('fromdb')
    csv_files = [f for f in os.listdir(data_folder) if f.startswith('bl-') and f.endswith('.csv')]
    if(len(csv_files) == 0):
        st.error("No battle log files found.")
        st.stop()
    df_list = []
    for i, file in stqdm(enumerate(csv_files), total=len(csv_files)):
        df_list.append(pd.read_csv(os.path.join(data_folder, file), header=None, encoding='utf-8'))
    merged_df = pd.concat(df_list, ignore_index=True)

    # merged_file = ut.get_work_file("fromdb/merged.csv")
    # merged_df.to_csv(merged_file, index=False, header=False, encoding='utf-8')
    # merged_df = pd.read_csv(merged_file, header=None, encoding='utf-8')

    # merged_df의 컬럼수가 37개인지 45개인지 확인
    is_full_log = len(merged_df.columns) == 45
    if not is_full_log and len(merged_df.columns) != 37:
        st.error(f"Unexpected number of columns: {len(merged_df.columns)}")
        st.stop()

    st.write("Change header to readable names.")
    bla.merge_name_for_battle_log_header(merged_df, is_full_log)

    st.write("Change ID to readable names.")
    bla.merge_name_for_battle_log_header(merged_df, is_full_log)
    
    # merged_df = pd.read_csv(ut.get_work_file("fromdb/merged.csv"), header=None, encoding='utf-8')
    st.write("Analyze battle logs by reason 30004...")
    bla.analyze_battle_logs_by_reason(merged_df, is_full_log)
    status.update(label="Analysis completed.", state="complete", expanded=False)

st.success("Analysis completed!")

st.subheader("연합간 전투 빈도 순위")
st.write(pd.read_csv(ut.get_work_path("result/연합간_전투_공방_빈도_순위.csv"), encoding='utf-8'))
st.subheader("연합간 전투 로그")
st.write(pd.read_csv(ut.get_work_path("result/연합간_전투_로그.csv"), encoding='utf-8'))
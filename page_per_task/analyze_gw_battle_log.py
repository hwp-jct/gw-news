import os
import sys
import time
import pandas as pd
import streamlit as st
from stqdm import stqdm

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils as ut
import game_log_analyzer as gla


if not ut.st_check_password():
    print(">>> check_password failed.")
    st.stop()

# cwd = os.path.dirname(os.path.abspath(__file__))
# os.chdir(cwd)

st.subheader("연합간 전투 로그 분석")

with st.sidebar:
    enc_type = os.getenv("ENC_TYPE", "utf-8")
    idx = 0 if enc_type == "utf-8" else 1
    enc_type = st.selectbox("select encoding type", ("utf-8", "utf-8-sig"), index=idx,
                             help="엑셀에서 정상적으로 보려면 utf-8-sig 선택.")
    os.environ["ENC_TYPE"] = enc_type

if not st.button("Start analyzing battle logs"):
    st.stop()

with st.status("Analyzing battle logs...", expanded=True) as status:
    st.write("Merging battle logs... 1/4")
    time.sleep(1)
    # merged_df = bla.merge_battle_logs() # 함수 그대로 복사해서 실행
    data_folder = ut.get_work_path('fromdb')
    csv_files = [f for f in os.listdir(data_folder) if f.startswith('bl-') and f.endswith('.csv')]
    if len(csv_files) == 0:
        st.error("No battle log files found.")
        st.stop()
    df_list = []
    for i, file in stqdm(enumerate(csv_files), total=len(csv_files)):
        df_list.append(ut.pd_read_csv(os.path.join(data_folder, file), header=None))
    merged_df = pd.concat(df_list, ignore_index=True)

    # merged_df의 컬럼수가 37개인지 45개인지 확인
    is_full_log = len(merged_df.columns) == 45
    if not is_full_log and len(merged_df.columns) != 37:
        st.error(f"Unexpected number of columns: {len(merged_df.columns)}")
        st.stop()

    st.write("Change header to readable names. 2/4")
    time.sleep(1)
    gla.merge_name_for_battle_log_header(merged_df, is_full_log)

    merged_file = ut.get_work_path("fromdb/merged.csv")
    st.write(f"Write to fromdb/merged.csv... 3/4")
    time.sleep(1)
    ut.df_write_csv(merged_df, merged_file, header=True, encoding=enc_type)
    # print(f">>> merged_df: {merged_file}")
    # merged_df = ut.pd_read_csv(merged_file, header=None)
    # merged_df = ut.pd_read_csv(ut.get_work_file("fromdb/merged.csv"), header=None)

    st.write("Analyze battle logs by reason 30004... 4/4")
    time.sleep(1)
    gla.analyze_battle_logs_by_reason(merged_df, is_full_log)
    status.update(label="Analysis completed.", state="complete", expanded=False)

st.success("Analysis completed!")

st.subheader("연합간 전투 빈도 순위")
st.write(ut.pd_read_csv(ut.get_work_path("result/연합간_전투_공방_빈도_순위.csv")))
st.subheader("연합간 전투 로그")
st.write(ut.pd_read_csv(ut.get_work_path("result/연합간_전투_로그.csv")))

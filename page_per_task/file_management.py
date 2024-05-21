import os
import re
import sys
import streamlit as st
from streamlit_file_browser import st_file_browser

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils as ut

if not ut.check_password():
    st.stop()

st.subheader('Upload ')
sub_folders = ('fromdb', 'result')
sub_folder = st.selectbox('Select upload folder', sub_folders, index=1)

# print("--- run ---")
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
uploaded_files = st.file_uploader("Choose a upload files", ['csv','txt'], accept_multiple_files=True)
if uploaded_files != st.session_state.uploaded_files:
    # print("upload file")
    for f in uploaded_files:
        if f in st.session_state.uploaded_files:
            continue
        if err := ut.save_uploaded_file(f, sub_folder) is not None:
            st.toast(f"❌ upload fail: {err}")
        else:
            st.toast(f"✔️ upload ok: {f.name}")
    st.session_state.uploaded_files = uploaded_files
    # st.rerun()

st.subheader('Uploaded File List')
event = st_file_browser(ut.get_work_path(),
                        # ignore_file_select_event=True,
                        file_ignores={"retain_parent": True, "rules": (re.compile(".*.exe"), re.compile(".*.ini"), re.compile(".*.xlsx"))},
                        key="A",
                        show_choose_file=False,
                        show_choose_folder=False,
                        show_delete_file=True,
                        # show_upload_file=True,
                        use_cache=False,
                        )
# st.write(event)
# print(event)
if event and event['type'] == 'DELETE_FILE':
    print("delete file")
    for item in event['target']:
        filepath = item['path']
        # print(f"delete file - {filepath}")
        if err := ut.delete_uploaded_file(filepath):
            st.toast(f"❌ delete fail: {err}")
        else:
            st.toast(f"✔️ delete ok: {filepath}")
            # st.rerun()

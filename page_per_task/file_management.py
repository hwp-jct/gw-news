import os
import re
import sys
import streamlit as st
from streamlit_file_browser import st_file_browser

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils as ut

if 'fm_run_cnt' not in st.session_state:
    st.session_state.fm_run_cnt = 0
st.session_state.fm_run_cnt += 1

if 'fm_uploaded' not in st.session_state:
    st.session_state.fm_uploaded = []

if 'fm_deleted' not in st.session_state:
    st.session_state.fm_deleted = []

if not ut.check_password():
    st.stop()

st.subheader('Upload ')
sub_folders = ('fromdb', 'result')
if 'sel_upload_folder' not in st.session_state:
    st.session_state.sel_upload_folder = "fromdb"
idx = sub_folders.index(st.session_state.sel_upload_folder)
st.session_state.sel_upload_folder = st.selectbox('Select upload folder', sub_folders, index=idx)

# print(f"--- run {st.session_state.fm_run_cnt} ---")

uploaded_files = st.file_uploader(
    "Choose a upload files",
    ['csv','txt', 'xlsx'],
    key="upload_files",
    # key=f"upload_files_{st.session_state.fm_run_cnt}",
    accept_multiple_files=True)

if uploaded_files:
    new_upload_files = []
    for f in uploaded_files:
        if f not in st.session_state.fm_uploaded:
            new_upload_files.append(f)
    st.session_state.fm_uploaded = uploaded_files

    err_list = []
    for f in new_upload_files:
        try:
            ut.save_uploaded_file(f, st.session_state.sel_upload_folder)
            print(f"upload file - {f.name}")
        except Exception as e:
            err_list.append(f"{f.name}: {e}")
            st.error(f"Error uploading {f.name}: {e}")

    if new_upload_files and not err_list:
        st.info(f"{len(uploaded_files)} files uploaded.") # force refresh st.file_browser

st.divider()
st.subheader('Uploaded File List')

event = st_file_browser(
        ut.get_work_path(),
        key="file_browser",
        # key=f"file_browser_{st.session_state.fm_run_cnt}",
        show_choose_file=False,
        show_choose_folder=False,
        show_delete_file=True,
        # show_upload_file=True,
        use_cache=False,
    )

if event and event['type'] == 'DELETE_FILE':
    # print(event)
    new_del_event = []
    for e in event['target']:
        if e not in st.session_state.fm_deleted:
            new_del_event.append(e)

    # print("delete file")
    for item in new_del_event:
        filepath = item['path']
        print(f"delete file - {filepath}")
        err = ut.delete_uploaded_file(filepath)
        if err is None:
            st.toast(f"✔️ delete ok: {filepath}")

    if len(new_del_event) > 0:
        st.session_state.fm_deleted = new_del_event
        # st.info(f"{len(new_del_event)} files deleted.") # force refresh st.file_browser
        st.rerun() # force refresh st.file_browser


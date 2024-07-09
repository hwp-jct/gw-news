import os
import re
import sys
import streamlit as st
from streamlit_file_browser import st_file_browser

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils as ut

st_ss = st.session_state

if 'fm_run_cnt' not in st.session_state:
    st_ss.fm_run_cnt = 0
st_ss.fm_run_cnt += 1

if 'saved_files' not in st.session_state:
    st_ss.saved_files = []

if 'fm_deleted' not in st.session_state:
    st_ss.fm_deleted = []

if not ut.st_check_password():
    st.stop()

print(f'dbg_run_fm---> {st_ss.fm_run_cnt}')

st.subheader('Select Upload Folder')
sub_folders = ('prompts', 'collect', 'testlog')
if 'sel_upload_folder' not in st.session_state:
    st_ss.sel_upload_folder = "prompts"
idx = sub_folders.index(st_ss.sel_upload_folder)

print(f"> selected upload folder! {st_ss.sel_upload_folder}")
sel_folder = st.selectbox('Select upload folder', sub_folders, label_visibility="collapsed", index=idx)
if sel_folder != st_ss.sel_upload_folder:
    st_ss.sel_upload_folder = sel_folder
    print(f"! chage upload folder to {sel_folder}")
    # st.rerun()
print(f"< selected upload folder! {st_ss.sel_upload_folder}")

print(f"> uploaded!")
uploaded_files = st.file_uploader(
    "Choose a upload files",
    ['csv','txt', 'xlsx'],
    key="upload_files",
    accept_multiple_files=True)
print(f"< uploaded!")

if uploaded_files:
    print(f"! process upload file!!")
    cnt_uploaded = 0
    for f in st_ss.upload_files:
        if st_ss.saved_files is None or f not in st_ss.saved_files:
            try:
                ut.save_uploaded_file(f, st_ss.sel_upload_folder)
                cnt_uploaded += 1
                print(f"! saved upload file - {f.name}")
            except Exception as e:
                st.error(f"Error uploading {f.name}: {e}")
    st_ss.saved_files = uploaded_files
    if cnt_uploaded > 0:
        print(f"! uploaded {cnt_uploaded} files.")
        st.rerun()

st.divider()
st.subheader('File List. Only delete file.')
print(f"> st_file_browser!!")
event = st_file_browser(
        ut.get_work_path(),
        key="file_browser",
        # key=f"file_browser_{st_ss.fm_run_cnt}",
        show_preview=False,
        show_choose_file=False,
        show_delete_file=True,
        show_upload_file=False,
        show_download_file=True,
        show_new_folder=False,
        use_cache=False,
    )
print(f"< st_file_browser!!")

if event and event['type'] == 'DELETE_FILE':
    print(f"! event proc st_file_browser!!")
    # print(event)
    new_del_event = []
    for e in event['target']:
        if e not in st_ss.fm_deleted:
            new_del_event.append(e)

    # print("delete file")
    for item in new_del_event:
        filepath = item['path']
        print(f"delete file - {filepath}")
        err = ut.delete_uploaded_file(filepath)
        if err is None:
            st.toast(f"✔️ delete ok: {filepath}")

    if len(new_del_event) > 0:
        st_ss.fm_deleted = new_del_event
        # st.info(f"{len(new_del_event)} files deleted.") # force refresh st.file_browser
        st.rerun() # force refresh st.file_browser

print(f'dbg_run_fm---< {st_ss.fm_run_cnt}')

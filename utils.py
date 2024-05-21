import os
import time
import hmac
import streamlit as st
import keyboard  # 키보드 입력 감지 라이브러리

from contextlib import contextmanager

QUIT_THREAD = False
PROJ_FOLDER = None
WORK_FOLDER = None
DONT_DISTRUB = False


def get_project_path():
    global PROJ_FOLDER
    if PROJ_FOLDER is not None:
        return PROJ_FOLDER
    PROJ_FOLDER = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(PROJ_FOLDER, 'app.py')):
        PROJ_FOLDER = os.path.dirname(PROJ_FOLDER)
    return PROJ_FOLDER


def get_work_path(file_or_folder=None):
    global WORK_FOLDER
    if WORK_FOLDER is None:
        WORK_FOLDER = os.path.join(get_project_path(), 'dist')
    if file_or_folder is None:
        return WORK_FOLDER
    return os.path.join(WORK_FOLDER, file_or_folder)


# 키보드 입력 감지를 위한 함수
def check_keyboard_input():
    global QUIT_THREAD
    while True:
        if keyboard.is_pressed('q'):
            QUIT_THREAD = True
            break
        time.sleep(0.1)  # 키보드 입력을 매 0.1초마다 확인


@contextmanager
def dont_disturb():
    global DONT_DISTRUB
    DONT_DISTRUB = True
    yield
    DONT_DISTRUB = False


# https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


def st_secrets(name):
    return st.secrets[name]


def print_log(msg):
    if(os.getenv("USE_STREAMLIT", "False") == "True"):
        if print_log.stwrite:
            print_log.stwrite(msg)
    else:
        print(msg)

print_log.stwrite = None


def save_uploaded_file(file, sub_path=None):
    folder = get_work_path(sub_path)
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_path = os.path.join(folder, file.name)
    try:
        with open(file_path, 'wb') as f:
           f.write(file.getbuffer())
           return None
    except Exception as e:
        return file_path # error


def delete_uploaded_file(filename, sub_path=None):
    folder = get_work_path(sub_path)
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return None
    else:
        return file_path # error
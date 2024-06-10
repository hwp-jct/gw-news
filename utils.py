import os
import time
import hmac
import pandas as pd
import streamlit as st
import keyboard  # 키보드 입력 감지 라이브러리

from contextlib import contextmanager

QUIT_THREAD = False
PROJ_FOLDER = None
WORK_FOLDER = None
DONT_DISTRUB = False


def is_quoted(s, quote='"'):
    return s.startswith(quote) and s.endswith(quote)


def strip_quotes(s, quote='"'):
    if is_quoted(s, quote):
        return s[1:-1]
    return s


def fix4_xl_str(s):
    if is_quoted(s):
        return s
    if s.startswith('=') or s.startswith('-'):
        return f'"{s}"'
    if ',' in s or ' ' in s:
        return f'"{s}"'
    return s

# ------------------------------------------------
# PATH Utilitiy Functions

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
        if not os.path.exists(WORK_FOLDER):
            os.makedirs(WORK_FOLDER)
    if file_or_folder is None:
        return WORK_FOLDER
    return os.path.join(WORK_FOLDER, file_or_folder)


# ------------------------------------------------
# Upload File Utility Functions

def save_txt_file(file_name, contents, sub_path=None):
    file_path = os.path.join(get_work_path(sub_path), file_name)
    with open(file_path, mode='w', encoding='utf-8') as f:
        f.write(contents)


def save_uploaded_file(file, sub_path=None):
    folder = get_work_path(sub_path)
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_path = os.path.join(folder, file.name)
    with open(file_path, mode='wb') as f:
        f.write(file.getbuffer())


def delete_uploaded_file(filename, sub_path=None):
    folder = get_work_path(sub_path)
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return None
    else:
        return file_path  # error


# ------------------------------------------------
# Keyboard Utility Functions

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


# ------------------------------------------------
# Streamlit Utility Functions

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


def st_secrets(key, section=None, model_name=None):
    if section and model_name:
        for model in st.secrets[section]['MODELS']:
            if model['NAME'] == model_name:
                return model[key]
    elif section:
        return st.secrets[section][key]
    else:
        return st.secrets[key]


def print_log(msg):
    if(os.getenv("USE_STREAMLIT", "False") == "True"):
        if print_log.stwrite:
            print_log.stwrite(msg)
    else:
        print(msg)

print_log.stwrite = None


# ------------------------------------------------
# File Utility Functions


def detect_encoding(file_path):
    import codecs
    with open(file_path, 'rb') as file:
        raw_data = file.read(4)  # BOM의 길이는 최대 4바이트이므로 처음 4바이트만 읽음
        if raw_data.startswith(codecs.BOM_UTF8):
            return 'utf-8-sig'
        elif raw_data[:2] in [codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE]:
            return 'utf-16'
        elif raw_data in [codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE]:
            return 'utf-32'
        else:
            return 'utf-8'


def open_utf_text_file(file_path, mode='r'):
    return open(file_path, mode, encoding=detect_encoding(file_path))


def pd_read_csv(file_path, *, header='infer'):
    return pd.read_csv(file_path, header=header, encoding=detect_encoding(file_path))


def df_write_csv(df, file_path, *, header=True, index=False, encoding='utf-8'):
    # print(f">>> Write to {file_path}")
    df.to_csv(file_path, header=header, index=index, encoding=encoding)
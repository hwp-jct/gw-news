import os
import re
import sys
import time
import streamlit as st

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils as ut
import llms as llm


# INIT ------------------------------------------------------------------------

st_ss = st.session_state

if not ut.st_check_password():
    # st.switch_page(st.seesion_state.pages["Home"][0])
    st.stop()

if "dbg_run_cnt" not in st_ss:
    st_ss.dbg_run_cnt = 0

st_ss.dbg_run_cnt += 1
print(f"dbg_run_cnt----->: {st_ss.dbg_run_cnt}")


# INTERNAL FUNCTIONS ----------------------------------------------------------

@st.cache_data
def get_llm_models(llm_type):
    return [md["NAME"] for md in ut.st_secrets("MODELS", llm_type)]


@st.experimental_fragment()
def st_wwn_sidebar():
    # st.caption("Select llm type(Azure or OpenAI)")
    # st.selectbox("llm type", ("OPENAI", "AZURE"), index=0, key="llm_type")
    # model_names = get_llm_models(st_ss.llm_type)
    model_names = get_llm_models("OPENAI")
    st.selectbox("select model", model_names, index=0, key="llm_model")
    st.slider("temperature", 0.0, 1.0, 0.7, 0.01, key="llm_temper")
    st.slider("top_p", 0.0, 1.0, 0.95, 0.01, key="llm_top_p")


@st.experimental_dialog("저장할 파일 이름을 입력하세요.")
def st_dialog_save_as_prompt():
    contents = st_ss.prompt_template
    filename = st_ss.prompt_file
    if not filename:
        filename = "prompt_???.txt"
    filename = st.text_input("파일 이름", value=filename)
    overwrite = st.checkbox("덮어 쓰기", key="overwrite_valid_file_name", value=False)
    print(f'> st_save_as_prompt_dialog ({filename})')

    if st.button("저장", key="save_valid_file_name", use_container_width=True):
        print('! save button clicked')
        if re.match(r'^[^<>:"/\\|?*]*\.txt$', filename):
            if not overwrite and os.path.exists(ut.get_work_path(f"prompts/{filename}")):
                st.warning("파일 이름이 이미 존재합니다.")
            else:
                ut.save_txt_file(filename, contents, "prompts")
                st_ss.prompt_file = filename
                print(f"! save as {filename}")
                # print(f"! save prompt\n```\n{contents}\n```")
                if filename != st_ss.prompt_file_opt[0]:
                    on_change_prompt_file_select()
                st.rerun()
        else:
            st.warning(f"파일 이름({filename})이 유효하지 않습니다.")
    print(f'< st_save_as_prompt_dialog')
    # return False


def _refresh_prompt_file_opt():
    w_dir = ut.get_work_path("prompts")
    st_ss.prompt_file_opt = [f for f in os.listdir(w_dir) if os.path.isfile(os.path.join(w_dir, f)) and f.endswith(".txt")]


def on_change_prompt_file_select():
    filename = st_ss.prompt_file
    print(f"! change prompt_file: {filename}")
    _refresh_prompt_file_opt()
    if not os.path.exists(os.path.join(ut.get_work_path("prompts"), filename)):
        st_ss.prompt_file_ = st_ss.prompt_file = None
        st.toast("파일이 존재하지 않습니다.", icon="🤔")
        return

    if filename in st_ss.prompt_file_opt:
        st_ss.prompt_file_opt.remove(filename)
        st_ss.prompt_file_opt.insert(0, filename)
    if filename is not None:
        filepath = os.path.join(ut.get_work_path("prompts"), filename)
        print(f"! load prompt file: {filepath}")
        st_ss.prompt_template = ut.open_utf_text_file(filepath).read()
    st_ss.prompt_file_ = st_ss.prompt_file  # session state에 저장


def _get_prompt_contents(fill_contents):
    if not st_ss.prompt_template:
        return {}, False
    contexts = re.findall(r'{(.*?)}', st_ss.prompt_template)
    contexts = list(set(contexts))  # 중복 제거
    p_params = {key: None for key in contexts}

    w_dir = ut.get_work_path("testlog")
    file_list = [f for f in os.listdir(w_dir) if os.path.isfile(os.path.join(w_dir, f))]

    for key, value in p_params.items():
        if '@' in key:
            p_params[key] = st_ss.get(f"c_{key}", None)
            if not p_params[key]:
                idx = None
                key_file = key.replace('@', '.')
                if key_file in file_list:
                    p_params[key] = key
        elif key == "language":
            p_params[key] = st_ss.get("c_lang_sel", "ko")
        else:
            p_params[key] = st_ss.get("c_" + key, None)

    if fill_contents:
        # contexts 마다 프로젝트의 data/testlog 폴더에 있는 파일을 선택할 수 있는 컴포넌트를 생성
        for key, value in p_params.items():
            # 파일 이름을 파일 내용으로 업데이트
            if '@' in key and value:
                key_file = key.replace('@', '.')
                file_path = os.path.join(w_dir, key_file)
                try:
                    with ut.open_utf_text_file(file_path) as file:
                        p_params[key] = file.read()
                except Exception as e:
                    st.error(f"파일 읽기 오류: {e}")
                    p_params[key] = None

    all_filled: bool = False
    if st_ss.prompt_template:
        if p_params:
            all_filled = all(bool(value) for value in p_params.values())
        else:
            all_filled = True
    return p_params, all_filled


@st.experimental_fragment()
def st_prompt_context(p_params):
    contexts = re.findall(r'{(.*?)}', st_ss.prompt_template)
    contexts = list(set(contexts))  # 중복 제거
    # contexts 마다 프로젝트의 data/testlog 폴더에 있는 파일을 선택할 수 있는 컴포넌트를 생성
    w_dir = ut.get_work_path("testlog")
    file_list = [f for f in os.listdir(w_dir) if os.path.isfile(os.path.join(w_dir, f))]

    for key, value in p_params.items():
        if '@' in key:
            p_params[key] = st_ss.get(f"c_{key}", None)
            if p_contexts[key]:
                st.selectbox(f":pencil2: {key}", file_list, key=f"c_{key}", placeholder="파일 이름을 선택하세요.")
            else:
                idx = None
                key_file = key.replace('@', '.')
                if key_file in file_list:
                    p_contexts[key] = key
                    idx = file_list.index(key_file)
                st.selectbox(f":pencil2: {key}", file_list, index=idx, key=f"c_{key}", placeholder="파일 이름을 선택하세요.")
        elif key == "language":
            st.selectbox(f":pencil2: {key}", ("ko", "en", "jp"), index=0, key="c_lang_sel")
        else:
            st.text_input(f":pencil2: {key}", key="c_" + key)


# MAIN =========================================================================

st_ss.llm_type = "OPENAI"

if "prompt_template" not in st_ss:
    st_ss.prompt_template = None

if "prompt_file_" not in st_ss:
    st_ss.prompt_file_ = None

if "prompt_file" not in st_ss:
    st_ss.prompt_file = st_ss.prompt_file_

with st.sidebar:
    st_wwn_sidebar()

if 'prompt_file_opt' not in st_ss:
    st_ss.prompt_file_opt = []
    _refresh_prompt_file_opt()

# PROMPRT FILE ----------------------------------------------------------------
print(f"> select prompt file {st_ss.prompt_file}")
if st_ss.get('refresh_prompt_file', False):
    _refresh_prompt_file_opt()

col_filelist, col_refresh = st.columns([1, 1])
# print(f"! prompt_file_opt: {st_ss.prompt_file_opt}")
col_filelist.selectbox(
    "load prompt file",
    st_ss.prompt_file_opt,
    placeholder="select a prompt file...",
    key='prompt_file',
    label_visibility="collapsed",
    on_change=on_change_prompt_file_select,
)
col_refresh.button("파일 목록 최신화", key="refresh_prompt_file", use_container_width=True)
print(f"< select prompt file {st_ss.prompt_file}")

# PROMPRT TEXT ----------------------------------------------------------------

prompt_text = st.text_area(
    ":pencil2: 프롬프트 템플릿",
    value=st_ss.prompt_template,
    height=280,
    placeholder="프롬프트 템플릿을 입력하거나 파일에서 로딩하세요.")
prompt_modified = st_ss.prompt_template != prompt_text
print(f"- prompt text is modified? {prompt_modified}")
# print(f"- prompt text is modified? {prompt_modified}:\n{st_ss.prompt_template}\n=>\n{prompt_text}")
st_ss.prompt_template = prompt_text

# SAVE PROMPT TEXT -----------------------------------------------------------

print(f'> save dialog buttons')
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("저장", key="save_prompt", use_container_width=True, disabled=not prompt_modified):
        if st_ss.prompt_file:
            ut.save_txt_file(st_ss.prompt_file, st_ss.prompt_template, "prompts")
            st.toast("저장되었습니다.", icon="😊")
        else:
            st_dialog_save_as_prompt()
with col2:
    if st.button("다른 이름으로 저장", key="save_as_prompt", use_container_width=True):
        st_dialog_save_as_prompt()
print(f'< save dialog buttons')

# PROMPRT TEMPLATE PARAMS -----------------------------------------------------

print(f'> fill prompt context')
if st_ss.prompt_template:
    p_contexts, ready_to_gen = _get_prompt_contents(False)
    cnt_context = sum(1 for value in p_contexts.values() if value)
    with st.expander(f"Prompt Template Parameters: Total {cnt_context}/{len(p_contexts)}", expanded=not ready_to_gen):
        st_prompt_context(p_contexts)
print(f'< fill prompt context')

# GENERATE NEWS ---------------------------------------------------------------

print(f'> generate news button')
p_contents, ready_to_gen = _get_prompt_contents(True)
if not ready_to_gen:
    st.warning("🤔 프롬프트와 템플릿 파라메터들을 채워주세요!")

if st_ss.get('exec_prompt', False):
    print(f'> on_generate_process')
    model = llm.get_llm(st_ss.llm_model, st_ss.llm_type, temperature=st_ss.llm_temper, top_p=st_ss.llm_top_p)

    output_parser = StrOutputParser()
    prompt = PromptTemplate.from_template(st_ss.prompt_template)

    chain = prompt | model | output_parser
    with st.spinner("생성 중..."):
        start_time = time.time()
        llm_result = chain.invoke(p_contents)
        end_time = time.time()
        elapsed_time = end_time - start_time
    print(f'< on_generate_process')
    st_ss.result = llm_result, elapsed_time

st.button("프롬프트 실행", key="exec_prompt", type="primary", disabled=not ready_to_gen, use_container_width=True)

# DISPLAY NEWS ----------------------------------------------------------------

if st_ss.get('clear_result', False):
    del st_ss.result

if "result" in st_ss and st_ss.result is not None:
    st.divider()
    info, cls = st.columns([1, 1], vertical_alignment="bottom")
    st.write(st_ss.result[0])
    info.write(f"duration : {st_ss.result[1]:.1f} seconds")
    cls.button("Clear", key="clear_result", use_container_width=True)
print(f'< generate news button')


print(f"dbg_run_cnt-----<: {st_ss.dbg_run_cnt}")

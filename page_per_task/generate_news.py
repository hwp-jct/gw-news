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

print("REFRESHED")
if not ut.st_check_password():
    # st.switch_page(st.seesion_state.pages["Home"][0])
    st.stop()

if "prompt_template" not in st_ss:
    st_ss.prompt_template = None

if "prompt_file" not in st_ss:
    st_ss.prompt_file = None

if "dbg_run_cnt" not in st_ss:
    st_ss.dbg_run_cnt = 0

st_ss.dbg_run_cnt += 1
print(f"dbg_run_cnt----->: {st_ss.dbg_run_cnt}")

prompt_cntxts = {}


# SIDEBAR LLM -----------------------------------------------------------------

@st.cache_data
def get_llm_models(llm_type):
    return [model["NAME"] for model in ut.st_secrets("MODELS", llm_type)]


with st.sidebar:
    st.caption("Select llm type(Azure or OpenAI)")
    st.selectbox("llm type", ("OPENAI", "AZURE"), index=0, key="llm_type")
    model_names = get_llm_models(st_ss.llm_type)
    st.selectbox("select model", model_names, index=0, key="llm_model")
    st.slider("temperature", 0.0, 1.0, 0.7, 0.01, key="llm_temper")
    st.slider("top_p", 0.0, 1.0, 0.95, 0.01, key="llm_top_p")


# PROMPT FILE -----------------------------------------------------------------

# LOAD PROMPT FILE ------------------------------------------------------------

def _refresh_prompt_file_opt():
    w_dir = ut.get_work_path("prompts")
    st_ss.prompt_file_opt = [f for f in os.listdir(w_dir) if os.path.isfile(os.path.join(w_dir, f)) and f.endswith(".txt")]

if 'prompt_file_opt' not in st_ss:
    st_ss.prompt_file_opt = []
    _refresh_prompt_file_opt()

# _refresh_prompt_file_opt()

def on_change_prompt_file_select():
    filename = st_ss.prompt_file
    print(f"! change prompt_file: {filename}")
    _refresh_prompt_file_opt()
    if not os.path.exists(os.path.join(ut.get_work_path("prompts"), filename)):
        st_ss.prompt_file = None
        st.toast("파일이 존재하지 않습니다.", icon="🤔")
        return
    if filename in st_ss.prompt_file_opt:
        st_ss.prompt_file_opt.remove(filename)
        st_ss.prompt_file_opt.insert(0, filename)
    if filename is not None:
        filepath = os.path.join(ut.get_work_path("prompts"), filename)
        print(f"! load prompt file: {filepath}")
        st_ss.prompt_template = ut.open_utf_text_file(filepath).read()


print(f"> select prompt file {st_ss.prompt_file}")
# print(f"! prompt_file_opt: {st_ss.prompt_file_opt}")
st.selectbox(
    "load prompt file",
    st_ss.prompt_file_opt,
    placeholder="select a prompt file...",
    key='prompt_file',
    label_visibility="collapsed",
    on_change=on_change_prompt_file_select,
)
print(f"< select prompt file {st_ss.prompt_file}")

# EDIT PROMPT TEXT ------------------------------------------------------------

prompt_text = st.text_area(
    ":pencil2: 프롬프트 템플릿",
    value=st_ss.prompt_template,
    height=280,
    placeholder="프롬프트 템플릿을 입력하거나 파일에서 로딩하세요.")
prompt_modified = st_ss.prompt_template != prompt_text
print(f"- prompt text is modified? {prompt_modified}")
# print(f"- prompt text is modified? {prompt_modified}:\n{st_ss.prompt_template}\n=>\n{prompt_text}")
st_ss.prompt_template = prompt_text


# SAVE PROMPT FILE ------------------------------------------------------------
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

# PROMPT CONTEXT -------------------------------------------------------------
print(f'> fill prompt context')
if st_ss.prompt_template:
    contexts = re.findall(r'{(.*?)}', st_ss.prompt_template)
    contexts = list(set(contexts))  # 중복 제거
    # contexts 마다 프로젝트의 data/testlog 폴더에 있는 파일을 선택할 수 있는 컴포넌트를 생성
    w_dir = ut.get_work_path("testlog")
    file_list = [f for f in os.listdir(w_dir) if os.path.isfile(os.path.join(w_dir, f))]
    prompt_cntxts = {key: None for key in contexts}

    for key, value in prompt_cntxts.items():
        if '@' in key:
            idx = None
            key_file = key.replace('@', '.')
            if key_file in file_list:
                prompt_cntxts[key] = key
                idx = file_list.index(key_file)
            prompt_cntxts[key] = st.selectbox(f":pencil2: {key}", file_list, index=idx, placeholder="파일 이름을 선택하세요.")
        elif key == "language":
            prompt_cntxts[key] = st.selectbox(f":pencil2: {key}", ("ko", "en", "jp"), index=0)
        else:
            prompt_cntxts[key] = st.text_input(f":pencil2: {key}", key="cntxt_"+key)

    # 파일 이름을 파일 내용으로 업데이트
    for key, value in prompt_cntxts.items():
        if '@' in key and value:
            file_path = os.path.join(w_dir, value)
            try:
                with ut.open_utf_text_file(file_path) as file:
                    prompt_cntxts[key] = file.read()
            except Exception as e:
                st.error(f"파일 읽기 오류: {e}")
                prompt_cntxts[key] = None
print(f'< fill prompt context')


# GENERATE NEWS ---------------------------------------------------------------
print(f'> generate news button')
ready_to_generate = all(bool(value) for value in prompt_cntxts.values())
print(f"! ready_to_generate: {ready_to_generate}")
if not ready_to_generate:
    st.warning("🤔 비어 있는 입력 항목이 있습니다!")
# else:
#     print(prompt_cntxts)

print(f'st_ss: {st_ss.llm_type}, {st_ss.llm_model}, {st_ss.llm_temper}, {st_ss.llm_top_p}')

if st.button(
        "프롬프트 실행",
        key="exec_prompt",
        type="primary",
        disabled=not ready_to_generate or st_ss.get('exec_prompt', False),  # or ut.DONT_DISTRUB,
        use_container_width=True):
    print(f'> on_generate_process')
    model = llm.get_llm(st_ss.llm_model, st_ss.llm_type, temperature=st_ss.llm_temper, top_p=st_ss.llm_top_p)

    output_parser = StrOutputParser()
    prompt = PromptTemplate.from_template(st_ss.prompt_template)

    chain = prompt | model | output_parser
    with st.spinner("생성 중..."):
        start_time = time.time()
        llm_result = chain.invoke(prompt_cntxts)
        end_time = time.time()
        elapsed_time = end_time - start_time
    print(f'< on_generate_process')
    st_ss.result = llm_result, elapsed_time
    st.rerun()  # button activation

# DISPLAY NEWS ----------------------------------------------------------------

if "result" in st_ss:
    st.divider()
    st.info(f"generation time : {st_ss.result[1]:.1f} seconds")
    st.write(st_ss.result[0])
print(f'< generate news button')


print(f"dbg_run_cnt-----<: {st_ss.dbg_run_cnt}")

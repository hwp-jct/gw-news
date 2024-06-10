import os
import re
import sys
import time
import json
import streamlit as st

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import utils as ut
import llms as llm


class StringImageOutputParser(BaseOutputParser):
    def parse(self, output: str):
        try:
            print(output)
            parsed_output = json.loads(output)
            text = parsed_output.get("text", "")
            image_url = parsed_output.get("image_url", "")
            return {"text": text, "image_url": image_url}
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format")

    def get_format_instructions(self):
        return "Expected format: {\"text\": \"<text>\", \"image_url\": \"<image_url>\"}"


@st.experimental_dialog("저장할 파일 이름을 입력하세요.")
def st_save_as_prompt(contents):
    file_name = st.text_input("파일 이름", value="prompt_[template].txt")
    overwrite = st.checkbox("덮어 쓰기", key="overwrite_valid_file_name", value=False)
    if st.button("저장", key="save_valid_file_name", use_container_width=True) and file_name:
        if re.match(r'^prompt_[^<>:"/\\|?*]*\.txt$', file_name):
            if not overwrite and os.path.exists(ut.get_work_path(f"fromdb/{file_name}")):
                st.warning("파일 이름이 이미 존재합니다.")
            else:
                ut.save_txt_file(file_name, contents, "fromdb")
                st.session_state.prompt_file = file_name
                st.rerun()
        else:
            st.warning("파일 이름이 유효하지 않습니다.")


if not ut.check_password():
    st.stop()

if "prompt_template" not in st.session_state:
    st.session_state.prompt_template = None

if "prompt_file" not in st.session_state:
    st.session_state.prompt_file = None

with st.sidebar:
    st.caption("Select llm type(Azure or OpenAI)")
    # secrets.toml의 AZURE와 OPENAI를 선택한 후 MODELS 중 하나를 선택할 수 있는 UI 생성
    llm_type = st.selectbox("llm type", ("AZURE", "OPENAI"), index=1)
    model_names = [model["NAME"] for model in ut.st_secrets("MODELS", llm_type)]
    model_name = st.selectbox("select model", model_names, index=0)
    model_temperature = st.slider("temperature", 0.0, 1.0, 0.7, 0.01)
    model_top_p = st.slider("top_p", 0.0, 1.0, 0.95, 0.01)
    work_dir = ut.get_work_path("fromdb")

file_list = [f for f in os.listdir(work_dir) if os.path.isfile(os.path.join(work_dir, f)) and f.endswith(".txt") and f.startswith("prompt")]
file_list.insert(0, None)
if st.session_state.prompt_file not in file_list:
    pf_idx = 0
else:
    pf_idx = file_list.index(st.session_state.prompt_file)
prompt_file = st.selectbox("load prompt file", file_list, index=pf_idx)
if prompt_file is not st.session_state.prompt_file:
    st.session_state.prompt_file = prompt_file
    # 경고 메시지 출력
    if(prompt_file is not None):
        st.session_state.prompt_template = ut.open_utf_text_file(os.path.join(work_dir, prompt_file)).read()

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("다른 이름으로 저장", key="save_as_prompt", use_container_width=True):
        st_save_as_prompt(st.session_state.prompt_template)
with col2:
    if st.button("저장", key="save_prompt", use_container_width=True):
        if prompt_file:
            ut.save_txt_file(prompt_file, st.session_state.prompt_template, "fromdb")
        else:
            st_save_as_prompt(st.session_state.prompt_template)

st.session_state.prompt_template = st.text_area(
    ":pencil2: 프롬프트 템플릿",
    value=st.session_state.prompt_template,
    height=280,
    placeholder="프롬프트 템플릿을 입력하거나 파일에서 로딩하세요.")

dict_contexts = {}
if st.session_state.prompt_template:
    # WN_PROMPT_TEMPLATE 문자열에서 "{}"로 둘러싸인 문자열을 찾아서 리스트로 저장
    contexts = re.findall(r'{(.*?)}', st.session_state.prompt_template)
    contexts = list(set(contexts))  # 중복 제거
    # contexts 마다 프로젝트의 dist/result 폴더에 있는 파일을 선택할 수 있는 컴포넌트를 생성
    work_dir = ut.get_work_path("result")
    file_list = [f for f in os.listdir(work_dir) if os.path.isfile(os.path.join(work_dir, f))]
    dict_contexts = {key: None for key in contexts}

    for key, value in dict_contexts.items():
        if key == "language":
            dict_contexts[key] = st.selectbox(f":pencil2: {key}", ("ko", "en", "jp"), index=0)
        else:
            idx = None
            key_csv = key + ".csv"
            if key_csv in file_list:
                dict_contexts[key] = key_csv
                idx = file_list.index(key_csv)
            dict_contexts[key] = st.selectbox(f":pencil2: {key}", file_list, index=idx, placeholder="파일 이름을 선택하세요.")

    # 파일 이름을 파일 내용으로 업데이트
    for key, value in dict_contexts.items():
        if key != "language" and value is not None:
            file_path = os.path.join(work_dir, value)
            with ut.open_utf_text_file(file_path) as file:
                dict_contexts[key] = file.read()

ready_to_generate = all(value is not None for value in dict_contexts.values())
if not ready_to_generate:
    st.warning("파일을 모두 선택해주세요.")

if st.button(
        "프롬프트 실행",
        key="exec_prompt",
        type="primary",
        disabled=not ready_to_generate, # or ut.DONT_DISTRUB,
        use_container_width=True):
    model = llm.get_llm(model_name, llm_type, temperature=model_temperature, top_p=model_top_p)
    
    output_parser = StrOutputParser()
    # output_parser = StringImageOutputParser()
    prompt = PromptTemplate.from_template(st.session_state.prompt_template)
    print(prompt)

    # print(st.session_state.prompt_template.format(**dict_contexts))

    chain = prompt | model | output_parser
    with st.spinner("생성 중..."):
        start_time = time.time()
        result = chain.invoke(dict_contexts)
        end_time = time.time()
        elapsed_time = end_time - start_time
        st.info(f"Execution time: {elapsed_time:.1f} seconds")
        st.write(result)
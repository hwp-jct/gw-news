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


WN_PROMPT_TEMPLATE = st.text_area(":pencil2: 프롬프트 템플릿", value=llm.WN_PROMPT_TEMPLATE, height=360)


if not ut.check_password():
    st.stop()

with st.sidebar:
    st.caption("Select llm type(Azure or OpenAI)")
    # secrets.toml의 AZURE와 OPENAI를 선택한 후 MODELS 중 하나를 선택할 수 있는 UI 생성
    llm_type = st.selectbox("llm type", ("AZURE", "OPENAI"), index=1)
    model_names = [model["NAME"] for model in ut.st_secrets("MODELS", llm_type)]
    model_name = st.selectbox("select model", model_names, index=0)

    # use_az = os.getenv("USE_AZURE") == "True"
    # use_az = st.toggle("Use Azure", use_az)
    # os.environ["USE_AZURE"] = str(use_az)

# WN_PROMPT_TEMPLATE 문자열에서 "{}"로 둘러싸인 문자열을 찾아서 리스트로 저장
contexts = re.findall(r'{(.*?)}', WN_PROMPT_TEMPLATE)
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
        with ut.open_file_dynamic_encoding(file_path) as file:
            dict_contexts[key] = file.read()

ready_to_generate = all(value is not None for value in dict_contexts.values())
if not ready_to_generate:
    st.warning("파일을 모두 선택해주세요.")

if st.button("프롬프트 실행", disabled=not ready_to_generate):
    model = llm.get_llm(model_name, llm_type)
    output_parser = StrOutputParser()
    prompt = PromptTemplate.from_template(WN_PROMPT_TEMPLATE)

    # print(WN_PROMPT_TEMPLATE.format(**dict_contexts))

    chain = prompt | model | output_parser
    with st.spinner("생성 중..."):
        start_time = time.time()
        result = chain.invoke(dict_contexts)
        end_time = time.time()
        elapsed_time = end_time - start_time
        st.info(f"Execution time: {elapsed_time:.1f} seconds")
        st.write(result)
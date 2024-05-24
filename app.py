import os
import utils as ut
import llms as llm
import streamlit as st

from st_pages import Page, Section, show_pages, add_page_title
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


# 런타임 전역 실행 환경 변수 설정
# os.environ["USE_AZURE"] = "False"
os.environ["USE_STREAMLIT"] = "True"

# ----------------------------------------------

def run_pure_python_test():
    file_path = ut.get_work_path("result/연합간공방순위.csv")
    with ut.open_file_dynamic_encoding(file_path) as file:
        context_1 = file.read()
    file_path = ut.get_work_path("result/연합공방전투로그.csv")
    with ut.open_file_dynamic_encoding(file_path) as file:
        context_2 = file.read()
    prompt = PromptTemplate.from_template("""
당신은 전쟁 게임 건십배틀의 종군기자 Davis입니다. 다음 주어진 context를 바탕으로 뉴스 기사를 사실적으로 작성해야 합니다.
뉴스는 흥미롭고 놀랄만한 사건을 다루어야 합니다. 또한, 기사 내용은 흥미진진하고 재미있게 작성해야 합니다. 
기사 작성은 {language} 언어로 작성해야 합니다.

<연합간 공방 순위 집계 테이블>    
{context_1}

<연합간 제독의 전투 로그>
{context_2}
""")
    model = llm.get_llm("gpt-4o", "OPENAI")
    output_parser = StrOutputParser()
    chain = prompt | model | output_parser
    # print(chain)
    print("Run!")
    print("Waiting for response...")
    print(chain.invoke({"context_1": context_1, "context_2": context_2, "language": "ko"}))

# ----------------------------------------------

def run_streamlit():
    st.subheader("월드 뉴스 생성 작업 순서")
    st.write("1. Collect Log : DB에서 로그 수집")
    st.write("2. Analysis Log : 로그 분석")
    st.write("3. Generate News : 뉴스 생성")

    show_pages(
        [Page("app.py", "Home", "🏠"),
         Page("page_per_task/file_management.py", "File Management", "📂"),
         Page("page_per_task/collect_gw_battle_log.py", "1. Collect Log"),
         Page("page_per_task/analyze_gw_battle_log.py", "2. Analysis Log"),
         Page("page_per_task/generate_news.py", "3. Generate News")],
    )


# ----------------------------------------------
if __name__ == '__main__':
    if not ut.check_password():
        st.stop()

    # upload folder check. if not exist, create it.
    up_folder = ut.get_work_path()
    if not os.path.exists(up_folder):
        os.makedirs(up_folder)
    up_folder = ut.get_work_path("fromdb")
    if not os.path.exists(up_folder):
        os.makedirs(up_folder)
    up_folder = ut.get_work_path("result")
    if not os.path.exists(up_folder):
        os.makedirs(up_folder)

    if os.getenv("USE_STREAMLIT") == "True":
        ut.print_log.stwrite = st.warning
        run_streamlit()
    else:
        run_pure_python_test()

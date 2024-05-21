import os
import utils as ut
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

WN_PROMPT_TEMPLATE = """
당신은 전쟁 게임 건십배틀의 종군기자 Davis입니다. 다음 주어진 context를 바탕으로 뉴스 기사를 사실적으로 작성해야 합니다.
뉴스는 흥미롭고 놀랄만한 사건을 다루어야 합니다. 또한, 기사 내용은 흥미진진하고 재미있게 작성해야 합니다. 
기사 작성은 {language} 언어로 작성해야 합니다.

<연맹간 공방 순위 집계 테이블>    
{context_1}

<연맹간 제독의 전투 로그>
{context_2}
"""


def get_llm():
    if os.getenv("USE_AZURE", "False") == "True":
        from langchain_openai import AzureChatOpenAI
        os.environ["AZURE_OPENAI_API_KEY"] = ut.st_secrets("AZURE_OPENAI_API_KEY")
        llm = AzureChatOpenAI(
            azure_endpoint=ut.st_secrets("AZURE_ENDPOINT"),
            openai_api_version="2024-02-15-preview",
            azure_deployment="ds-gpt4"
        )
    else:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            temperature=0,
            openai_api_key=ut.st_secrets("OPENAI_API_KEY"),
            model_name="gpt-4-turbo-preview",
        )
    return llm


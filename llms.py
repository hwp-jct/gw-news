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


def get_llm(model_name, section):
    # if os.getenv("USE_AZURE", "False") == "True":
    if section == "AZURE":
        from langchain_openai import AzureChatOpenAI
        os.environ["AZURE_OPENAI_API_KEY"] = ut.st_secrets("API_KEY", section)
        llm = AzureChatOpenAI(
            azure_endpoint=ut.st_secrets("ENDPOINT", section, model_name),
            openai_api_version=ut.st_secrets("API_VERSION", section, model_name),
            azure_deployment=ut.st_secrets("DEPLOYMENT", section, model_name)
        )
    else:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            temperature=0,
            openai_api_key=ut.st_secrets("API_KEY", section),
            model_name=ut.st_secrets("NAME", section, model_name),
        )
    return llm



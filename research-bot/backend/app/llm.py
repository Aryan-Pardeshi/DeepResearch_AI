import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

llm = ChatOpenAI(
    model="deepseek-v4-flash",
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base=os.getenv("DEEPSEEK_BASE_URL")
)

llm1 = llm
# llm1 = ChatOpenAI(
#     model="deepseek-v4-flash",
#     openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
#     openai_api_base=os.getenv("DEEPSEEK_BASE_URL"),
#     extra_body={"thinking": {"type": "disabled"}}
# )


llm2 = ChatOpenAI(
    model="deepseek-v4-pro",
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base=os.getenv("DEEPSEEK_BASE_URL")
)


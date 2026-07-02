import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


class _LazyLLM:
    def __init__(self):
        self._instance = None

    def _get(self):
        if self._instance is None:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "DEEPSEEK_API_KEY is not set. "
                    "Set it in the .env file or via the settings modal."
                )
            self._instance = ChatOpenAI(
                model="deepseek-chat",
                openai_api_key=api_key,
                openai_api_base=os.getenv("DEEPSEEK_BASE_URL"),
                timeout=60,
                max_retries=2,
            )
        return self._instance

    def reset(self):
        self._instance = None

    def __getattr__(self, name):
        return getattr(self._get(), name)


llm = _LazyLLM()
# llm_fast = llm
# llm_pro = llm
llm_fast = ChatOpenAI(
    model="deepseek-v4-flash",
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base=os.getenv("DEEPSEEK_BASE_URL"),
    extra_body={"thinking": {"type": "disabled"}},
)

llm_pro = ChatOpenAI(
    model="deepseek-v4-flash",
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base=os.getenv("DEEPSEEK_BASE_URL"),
)

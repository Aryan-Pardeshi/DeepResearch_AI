import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


def get_llm_config():
    api_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
    return api_key, base_url


def get_llm(model: str | None = None, role: str | None = None, temperature: float = 0.0) -> ChatOpenAI:
    api_key, base_url = get_llm_config()
    if not api_key or api_key == "your_api_key_here" or api_key == "your_key_here":
        raise RuntimeError(
            "LLM_API_KEY is not set. "
            "Set it in the .env file or via the settings modal."
        )

    if not model:
        if role == "planner":
            model = os.getenv("LLM_MODEL_PLANNER", "deepseek-chat")
        elif role == "researcher":
            model = os.getenv("LLM_MODEL_RESEARCHER", "deepseek-chat")
        elif role == "aggregator":
            model = os.getenv("LLM_MODEL_AGGREGATOR", "deepseek-chat")
        else:
            model = os.getenv("LLM_MODEL_PLANNER", "deepseek-chat")

    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=temperature
    )


class _LazyLLM:
    def __init__(self, role: str | None = None, model_override: str | None = None):
        self._role = role
        self._model_override = model_override
        self._instance = None

    def _get(self):
        if self._instance is None:
            self._instance = get_llm(model=self._model_override, role=self._role)
        return self._instance

    def reset(self):
        self._instance = None

    def __getattr__(self, name):
        return getattr(self._get(), name)


llm = _LazyLLM()
lazy_llm = llm
llm_fast = _LazyLLM(role="researcher")
llm_pro = _LazyLLM(role="aggregator")

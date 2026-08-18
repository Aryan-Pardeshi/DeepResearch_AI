import os
import logging
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class LoggingSQLiteCache(SQLiteCache):
    def lookup(self, prompt: str, llm_string: str):
        result = super().lookup(prompt, llm_string)
        prefix = (prompt[:50] + "...") if len(prompt) > 50 else prompt
        if result is not None:
            logger.info(f"[LLM CACHE HIT] Prompt: {prefix!r}")
        else:
            logger.info(f"[LLM CACHE MISS] Prompt: {prefix!r}")
        return result


def init_llm_cache():
    cache_path_str = os.getenv("LLM_CACHE_PATH", "./data/llm_cache.db")
    cache_path = Path(cache_path_str).resolve()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    set_llm_cache(LoggingSQLiteCache(database_path=str(cache_path)))
    logger.info(f"LLM cache initialized at {cache_path}")


init_llm_cache()



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

    # max_retries=0: LangChain/openai-client retries run inside a thread executor,
    # which means asyncio.wait_for() cannot cancel them. A single stuck request
    # with max_retries=1 can block for 2×request_timeout before returning.
    # Our _safe_invoke_llm() already handles retries with proper async backoff.
    timeout_val = float(os.getenv("LLM_REQUEST_TIMEOUT", "60.0"))
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=temperature,
        request_timeout=timeout_val,
        max_retries=0
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


# Structured output is not implemented the same way everywhere. LLM_BASE_URL can
# point at any OpenAI-compatible gateway, and they disagree: some reject
# response_format={"type":"json_object"} outright with a 400 on the
# response_format parameter, others do not implement json_schema. Rather than
# hardcoding one method, try them in order and remember what worked.
STRUCTURED_METHODS = ("json_schema", "function_calling", "json_mode")

_structured_method_cache: dict[tuple[str, str], str] = {}


def invoke_structured(base_llm, schema, prompt):
    """Invokes an LLM with structured output, negotiating the method per provider.

    Returns the parsed schema instance. Raises the last error only if no method
    worked, so a provider that supports none of them still surfaces a real error.
    """
    model = getattr(base_llm, "model_name", "?")
    base = str(getattr(base_llm, "openai_api_base", "") or "")
    key = (base, model)

    methods = STRUCTURED_METHODS
    cached = _structured_method_cache.get(key)
    if cached:
        methods = (cached,) + tuple(m for m in STRUCTURED_METHODS if m != cached)

    last_error = None
    for method in methods:
        try:
            result = base_llm.with_structured_output(schema, method=method).invoke(prompt)
            if result is None:
                # The call succeeded but produced nothing usable; try the next method
                # rather than handing a None back to the caller.
                last_error = ValueError(f"{method} returned no parsed output")
                continue
            if _structured_method_cache.get(key) != method:
                logger.info(f"Structured output via '{method}' for {model} at {base}")
                _structured_method_cache[key] = method
            return result
        except Exception as e:
            last_error = e
            logger.debug(f"Structured output method '{method}' failed for {model}: {e}")

    raise last_error if last_error else RuntimeError("Structured output failed")

import sys, os, re
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.api.agent import router as agent_router
from backend.app.llm import lazy_llm, llm_fast, llm_pro

from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
ENV_PATH = root_dir / ".env"

app = FastAPI(title="AI Research Assistant Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)

# Mount static directory for serving charts
static_path = Path(__file__).resolve().parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/")
def read_root():
    return {"status": "running", "message": "Research Bot API is up and running"}

def _get_config_status():
    llm_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    llm_url = os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
    tavily_key = os.getenv("TAVILY_API_KEY")
    openalex_email = os.getenv("OPENALEX_EMAIL")
    
    placeholders = {"your_api_key_here", "your_key_here", "your_email@example.com", ""}
    
    missing_required = []
    if not llm_key or llm_key.strip() in placeholders:
        missing_required.append("LLM_API_KEY")
    if not tavily_key or tavily_key.strip() in placeholders:
        missing_required.append("TAVILY_API_KEY")
        
    return {
        "ok": len(missing_required) == 0,
        "llm_base_url": llm_url,
        "llm_api_key_configured": bool(llm_key) and llm_key.strip() not in placeholders,
        "tavily_configured": bool(tavily_key) and tavily_key.strip() not in placeholders,
        "llm_model_planner": os.getenv("LLM_MODEL_PLANNER", "deepseek-chat"),
        "llm_model_researcher": os.getenv("LLM_MODEL_RESEARCHER", "deepseek-chat"),
        "llm_model_aggregator": os.getenv("LLM_MODEL_AGGREGATOR", "deepseek-chat"),
        "openalex_email": openalex_email or "",
        "semantic_scholar_api_key_configured": bool(os.getenv("SEMANTIC_SCHOLAR_API_KEY")),
        "core_api_key_configured": bool(os.getenv("CORE_API_KEY")),
        "missing_required": missing_required,
        "issues": [f"{k} is not set or using placeholder" for k in missing_required]
    }

@app.get("/config/status")
@app.get("/health/config")
def check_config():
    return _get_config_status()

class ConfigUpdate(BaseModel):
    LLM_BASE_URL: str | None = None
    LLM_API_KEY: str | None = None
    LLM_MODEL_PLANNER: str | None = None
    LLM_MODEL_RESEARCHER: str | None = None
    LLM_MODEL_AGGREGATOR: str | None = None
    OPENALEX_EMAIL: str | None = None
    SEMANTIC_SCHOLAR_API_KEY: str | None = None
    CORE_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None

def _apply_config_update(body: ConfigUpdate):
    updated = []
    try:
        content = ENV_PATH.read_text() if ENV_PATH.exists() else ""
        lines = content.splitlines(keepends=True)

        def upsert(key, value):
            if value is None:
                return
            for i, line in enumerate(lines):
                if line.strip().startswith(key + "=") or line.strip().startswith(key + " ="):
                    lines[i] = f'{key}="{value}"\n'
                    return
            lines.append(f'{key}="{value}"\n')

        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            if v is not None:
                upsert(k, v)
                os.environ[k] = str(v)
                updated.append(k)

        ENV_PATH.write_text("".join(lines))
        load_dotenv(dotenv_path=ENV_PATH, override=True)

        lazy_llm.reset()
        llm_fast.reset()
        llm_pro.reset()

        return {"ok": True, "updated": updated, "message": "Applied configuration changes successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/setup")
@app.post("/health/config")
def update_config(body: ConfigUpdate):
    return _apply_config_update(body)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

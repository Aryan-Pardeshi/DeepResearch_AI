from contextlib import asynccontextmanager
import sys, os, re, secrets
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.api.agent import router as agent_router
from backend.app.api.research_mode import router as research_mode_router
from backend.app.llm import lazy_llm, llm_fast, llm_pro
from backend.app.graph.research_mode_builder import set_checkpointer as set_rm_checkpointer
from backend.app.graph.builder import set_checkpointer as set_ds_checkpointer

from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
ENV_PATH = root_dir / ".env"


def _config_api_token() -> str:
    return os.getenv("CONFIG_API_TOKEN", "").strip()


def _config_api_is_open() -> bool:
    return os.getenv("ALLOW_OPEN_CONFIG_API", "").strip().lower() in {"1", "true", "yes"}


def _authorize_config_write(token: str | None) -> None:
    """Guards the endpoints that rewrite .env.

    This API can overwrite LLM_API_KEY and repoint LLM_BASE_URL, so it fails closed:
    without CONFIG_API_TOKEN set, or ALLOW_OPEN_CONFIG_API opted in for local work,
    it stays shut. A public deployment that forgets to configure anything is locked,
    not wide open.
    """
    expected = _config_api_token()
    if expected:
        if not token or not secrets.compare_digest(token, expected):
            raise HTTPException(status_code=401, detail="Invalid or missing X-Config-Token header")
        return
    if _config_api_is_open():
        return
    raise HTTPException(
        status_code=403,
        detail="Configuration API is disabled. Set CONFIG_API_TOKEN, or ALLOW_OPEN_CONFIG_API=1 for local use."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path_str = os.getenv("RESEARCH_DB_PATH", "./data/research_state.db")
    db_path = Path(db_path_str).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        await checkpointer.setup()
        set_rm_checkpointer(checkpointer)
        set_ds_checkpointer(checkpointer)
        yield


app = FastAPI(title="AI Research Assistant Bot", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)
app.include_router(research_mode_router)

# Mount static directory for serving charts
static_path = Path(__file__).resolve().parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

frontend_path = root_dir / "frontend"


@app.get("/healthz")
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
        # Only echoed back when the config API is locally open; on a public
        # deployment this is somebody's personal address.
        "openalex_email": (openalex_email or "") if _config_api_is_open() else "",
        "config_writable": _config_api_is_open() or bool(_config_api_token()),
        "config_requires_token": bool(_config_api_token()),
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
def update_config(body: ConfigUpdate, x_config_token: str | None = Header(None, alias="X-Config-Token")):
    _authorize_config_write(x_config_token)
    return _apply_config_update(body)


# Dedicated SEO and Crawler File Handlers
@app.get("/robots.txt", include_in_schema=False)
def serve_robots():
    robots_file = frontend_path / "robots.txt"
    if robots_file.exists():
        return FileResponse(robots_file, media_type="text/plain")
    raise HTTPException(status_code=404, detail="robots.txt not found")

@app.get("/sitemap.xml", include_in_schema=False)
def serve_sitemap():
    sitemap_file = frontend_path / "sitemap.xml"
    if sitemap_file.exists():
        return FileResponse(sitemap_file, media_type="application/xml")
    raise HTTPException(status_code=404, detail="sitemap.xml not found")

@app.get("/site.webmanifest", include_in_schema=False)
def serve_manifest():
    manifest_file = frontend_path / "site.webmanifest"
    if manifest_file.exists():
        return FileResponse(manifest_file, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="site.webmanifest not found")

# Serve the UI from the application root. Registered last so every API route above
# keeps precedence: a mount at "/" would otherwise swallow them.
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend_ui")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)

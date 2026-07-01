import sys, os, re
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.api.agent import router as agent_router

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

@app.get("/")
def read_root():
    return {"status": "running", "message": "Research Bot API is up and running"}

@app.get("/health/config")
def check_config():
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    issues = []
    if not deepseek_key or deepseek_key == "your_key_here":
        issues.append("DEEPSEEK_API_KEY is not set in .env")
    if not tavily_key or tavily_key == "your_key_here":
        issues.append("TAVILY_API_KEY is not set in .env")
    return {
        "ok": len(issues) == 0,
        "deepseek_configured": bool(deepseek_key) and deepseek_key != "your_key_here",
        "tavily_configured": bool(tavily_key) and tavily_key != "your_key_here",
        "issues": issues
    }

class ConfigUpdate(BaseModel):
    DEEPSEEK_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None

@app.post("/health/config")
def update_config(body: ConfigUpdate):
    updated = []
    try:
        content = ENV_PATH.read_text() if ENV_PATH.exists() else ""
        lines = content.splitlines(keepends=True)
        seen_keys = set()

        def upsert(key, value):
            seen_keys.add(key)
            for i, line in enumerate(lines):
                if line.strip().startswith(key + "="):
                    lines[i] = f'{key} = "{value}"\n'
                    return
            lines.append(f'{key} = "{value}"\n')

        if body.DEEPSEEK_API_KEY:
            upsert("DEEPSEEK_API_KEY", body.DEEPSEEK_API_KEY)
            updated.append("DEEPSEEK_API_KEY")
        if body.TAVILY_API_KEY:
            upsert("TAVILY_API_KEY", body.TAVILY_API_KEY)
            updated.append("TAVILY_API_KEY")

        ENV_PATH.write_text("".join(lines))
        load_dotenv(override=True)
        for k in updated:
            os.environ[k] = body.model_dump()[k]

        return {"ok": True, "updated": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

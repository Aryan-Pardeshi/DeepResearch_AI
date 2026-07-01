import sys
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.api.agent import router as agent_router

from fastapi.middleware.cors import CORSMiddleware

# Load environment variables (.env file from root or backend directory)
load_dotenv()

app = FastAPI(title="AI Research Assistant Bot")

# Allow all origins, methods, and headers for local development
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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

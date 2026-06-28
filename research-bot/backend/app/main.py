import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables (.env file from root or backend directory)
load_dotenv()

app = FastAPI(title="AI Research Assistant Bot")


@app.get("/")
def read_root():
    return {"status": "running", "message": "Research Bot API is up and running"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

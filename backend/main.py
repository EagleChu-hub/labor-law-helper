from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers import check, ask, law

app = FastAPI(title="勞基法查詢小幫手 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 公開工具，允許任意來源
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(check.router, prefix="/api/v1/check", tags=["check"])
app.include_router(ask.router, prefix="/api/v1/ask", tags=["ask"])
app.include_router(law.router, prefix="/api/v1/law", tags=["law"])


@app.get("/")
def health_check():
    return {"status": "ok", "service": "勞基法查詢小幫手"}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .academic_router import router as academic_router
from .auth_router import router as auth_router
from .settings import settings
from .setup_router import router as setup_router

app = FastAPI(title="ExamFlow ERP API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(setup_router)
app.include_router(auth_router)
app.include_router(academic_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "examflow-api"}

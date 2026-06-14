from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import jobs, clips, campaigns

app = FastAPI(
    title="ClipOS API",
    description="AI-powered Whop clipping automation backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(clips.router, prefix="/clips", tags=["Clips"])
app.include_router(campaigns.router, prefix="/campaigns", tags=["Campaigns"])


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ClipOS API"}
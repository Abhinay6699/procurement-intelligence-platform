from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .routers import auth, upload, analyze, vendors, dashboard, reports, agent_trace

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Procurement Leakage Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(analyze.router, prefix="/analyze", tags=["analyze"])
app.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(agent_trace.router, prefix="/agent-trace", tags=["agent_trace"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Procurement Leakage Detection API"}

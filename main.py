"""
Profitoracle — FastAPI Backend
Exposes /analyze, /history, and /health endpoints.
Invokes the LangGraph pipeline and manages file lifecycle.
"""

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from utils.file_utils import save_upload, delete_file
from utils.db import init_db, insert_run, get_history
from graph.graph import get_app


# ── Lifespan: create directories and init DB on startup ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data", exist_ok=True)
    os.makedirs("uploads", exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title="Profitoracle — Validator Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS for Streamlit (localhost:8501) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── POST /analyze ──

@app.post("/analyze")
async def analyze(file: UploadFile = File(...), query: str = Form(...)):
    """
    Accept a spreadsheet file and a user query.
    Run the full LangGraph pipeline and return the result.
    """
    file_path = None
    try:
        # Save uploaded file
        file_bytes = await file.read()
        file_path = save_upload(file_bytes, file.filename)

        # Build initial state for the LangGraph pipeline
        initial_state = {
            "user_query": query,
            "file_path": file_path,
            "file_df": None,
            "validation_errors": [],
            "plan": "",
            "generated_code": "",
            "exec_output": None,
            "exec_error": None,
            "verdict": "",
            "retry_count": 0,
            "final_answer": "",
            "status": "pending",
        }

        # Invoke the compiled LangGraph pipeline
        result = get_app().invoke(initial_state)

        # Extract response fields
        status = result.get("status", "failed")
        final_answer = result.get("final_answer", "No answer produced.")
        retry_count = result.get("retry_count", 0)
        validation_errors = result.get("validation_errors", [])

        # Log to SQLite
        insert_run(
            query=query,
            filename=file.filename,
            status=status,
            retry_count=retry_count,
            final_answer=final_answer,
        )

        return JSONResponse(content={
            "status": status,
            "final_answer": final_answer,
            "retry_count": retry_count,
            "validation_errors": validation_errors,
        })

    except Exception as e:
        # Log the failed run
        insert_run(
            query=query,
            filename=file.filename if file else "unknown",
            status="failed",
            retry_count=0,
            final_answer=f"Server error: {str(e)}",
        )
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Always clean up the uploaded file
        if file_path:
            delete_file(file_path)


# ── GET /history ──

@app.get("/history")
async def history():
    """Return the last 20 analysis runs from SQLite."""
    runs = get_history(limit=20)
    return JSONResponse(content=runs)


# ── GET /health ──

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

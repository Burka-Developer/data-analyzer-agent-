"""
SheetQA — FastAPI Backend
Exposes /analyze, /history, and /health endpoints.
Invokes the LangGraph pipeline and manages file lifecycle.
"""

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

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
    title="SheetQA — Validator Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS — allow frontend from any origin ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Serve Frontend ──

@app.get("/")
async def read_index():
    """Serve the main frontend page."""
    return FileResponse("frontend/index.html")


@app.get("/docs.html")
async def read_docs():
    """Serve the documentation page."""
    return FileResponse("docs.html")


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

        # Extract agent's intermediate work for transparency
        plan = result.get("plan", "")
        generated_code = result.get("generated_code", "")
        exec_output = result.get("exec_output", "")
        exec_error = result.get("exec_error", "")
        verdict = result.get("verdict", "")

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
            "plan": plan,
            "generated_code": generated_code,
            "exec_output": exec_output,
            "exec_error": exec_error,
            "verdict": verdict,
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


# ── Run with: python main.py ──

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  SheetQA — Validator Agent API")
    print("  Starting server on http://0.0.0.0:7860")
    print("  Docs available at http://0.0.0.0:7860")
    print("=" * 60)
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=True)


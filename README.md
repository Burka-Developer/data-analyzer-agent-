# Profitoracle — Data Validator Agent

A multi-agent pipeline that accepts a user query and a CSV/spreadsheet file, performs layered validation and intelligent data analysis, executes self-written Python code locally, verifies the output, and returns a final answer to the user.

## Architecture

```
User Input (Query + CSV)
        │
        ▼
┌─────────────────┐
│  File Validator  │──── Fail ──▶ Rejection Handler ──▶ Error Message
│  (Python logic)  │
└────────┬────────┘
         │ Pass
         ▼
┌──────────────────────────────────────────┐
│         Data Validator Agent             │
│                                          │
│  ┌────────────────┐                      │
│  │ Planning Agent  │◀──── Re-plan ◄──┐   │
│  │     (Groq)     │                 │   │
│  └───────┬────────┘                 │   │
│          ▼                          │   │
│  ┌────────────────┐                 │   │
│  │ Execution Agent │                 │   │
│  │     (Groq)     │                 │   │
│  └───────┬────────┘                 │   │
│          ▼                          │   │
│  ┌────────────────┐                 │   │
│  │ Validator Agent │── Mismatch ────┘   │
│  │     (Groq)     │                     │
│  └───────┬────────┘                     │
│          │ Match                         │
└──────────┼───────────────────────────────┘
           ▼
    ┌──────────────┐
    │ Final Answer  │
    └──────────────┘
```

## Tech Stack

| Layer            | Technology                              |
|------------------|-----------------------------------------|
| LLM API          | Groq (via OpenAI-compatible client)     |
| AI Framework     | LangGraph + LangChain                   |
| Backend API      | FastAPI (Python 3.11+)                  |
| Frontend UI      | Streamlit                               |
| Code Sandbox     | RestrictedPython (secure local exec)    |
| Database         | SQLite3 (conversation + run history)    |
| Data Processing  | pandas, numpy, scikit-learn             |

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure your API key:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your Groq API key.

3. Start the backend (Terminal 1):
   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. Start the frontend (Terminal 2):
   ```bash
   streamlit run frontend/app.py
   ```

5. Open http://localhost:8501 in your browser.

## Project Structure

```
profitoracle/
├── .env                    ← GROQ_API_KEY=your_key_here
├── .env.example            ← GROQ_API_KEY=
├── requirements.txt
├── README.md
├── main.py                 ← FastAPI app + uvicorn entry
├── graph/
│   ├── __init__.py
│   ├── state.py            ← AgentState TypedDict definition
│   ├── nodes.py            ← All 5 node functions
│   ├── edges.py            ← All routing functions
│   └── graph.py            ← LangGraph StateGraph builder + compile()
├── utils/
│   ├── __init__.py
│   ├── file_utils.py       ← File save, parse, delete helpers
│   ├── code_runner.py      ← RestrictedPython executor
│   └── db.py               ← SQLite3 insert + query helpers
├── data/                   ← Auto-created, holds runs.db
├── uploads/                ← Auto-created, temp file storage
└── frontend/
    └── app.py              ← Streamlit UI
```

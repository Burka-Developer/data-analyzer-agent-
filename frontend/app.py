"""
Profitoracle — Streamlit Frontend
Single-page UI for uploading spreadsheets and querying the Validator Agent.
"""

import streamlit as st
import requests

# ── Page Configuration ──
st.set_page_config(
    page_title="Profitoracle — Data Validator Agent",
    page_icon="📊",
    layout="centered",
)

API_URL = "http://localhost:8000"

# ── Custom CSS for styling ──
st.markdown("""
<style>
    .stApp {
        background-color: #0F172A;
    }
    .main-header {
        background: linear-gradient(135deg, #3B82F6, #8B5CF6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #94A3B8;
        text-align: center;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    .result-box {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar: Tech Stack ──
with st.sidebar:
    st.markdown("### 🧱 Tech Stack")
    st.info("🖥️ **Backend:** FastAPI (Python)")
    st.info("🎨 **Frontend:** Streamlit")
    st.info("🧠 **AI Framework:** LangGraph + LangChain")
    st.info("🤖 **LLM:** xAI Grok")
    st.info("🛡️ **Security:** RestrictedPython Sandbox")
    st.info("🗄️ **Database:** SQLite3")
    st.info("📊 **Data Processing:** Pandas, NumPy, Scikit-learn")

    st.markdown("---")
    st.markdown("### 📜 Recent Runs")
    if st.button("🔄 Load History", use_container_width=True):
        try:
            resp = requests.get(f"{API_URL}/history", timeout=5)
            if resp.status_code == 200:
                history = resp.json()
                if history:
                    for run in history[:10]:
                        status_icon = (
                            "✅" if run.get("status") == "success"
                            else "❌" if run.get("status") == "rejected"
                            else "⚠️"
                        )
                        st.markdown(
                            f"{status_icon} **{run.get('filename', 'N/A')}** — "
                            f"`{run.get('status', 'unknown')}`"
                        )
                        st.caption(run.get("query", "")[:80])
                else:
                    st.caption("No runs recorded yet.")
            else:
                st.error("Failed to load history.")
        except requests.ConnectionError:
            st.error("Backend not reachable. Is the API running?")


# ── Main Content ──
st.markdown('<div class="main-header">Profitoracle</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Data Validator Agent — Upload, Ask, Analyze</div>',
    unsafe_allow_html=True,
)

# File uploader
uploaded_file = st.file_uploader(
    "📁 Upload your spreadsheet",
    type=["csv", "xlsx", "xls"],
    help="Accepted formats: CSV, XLSX, XLS. Max 10MB, 50,000 rows.",
)

# Query input
query = st.text_area(
    "💬 Ask a question about your data",
    placeholder="e.g., What is the total revenue by region?",
    height=100,
)

# Analyze button
analyze_clicked = st.button("🚀 Analyze", type="primary", use_container_width=True)

if analyze_clicked:
    # Validate inputs on the client side
    if not uploaded_file:
        st.error("Please upload a file first.")
    elif not query or not query.strip():
        st.error("Please enter a question about your data.")
    else:
        with st.spinner("🤖 Agent is thinking... This may take a moment."):
            try:
                # POST to FastAPI backend
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type,
                    )
                }
                data = {"query": query.strip()}

                response = requests.post(
                    f"{API_URL}/analyze",
                    files=files,
                    data=data,
                    timeout=120,
                )

                if response.status_code == 200:
                    result = response.json()
                    status = result.get("status", "unknown")
                    final_answer = result.get("final_answer", "No answer.")
                    retry_count = result.get("retry_count", 0)
                    validation_errors = result.get("validation_errors", [])

                    st.markdown("---")

                    if status == "success":
                        st.success("✅ Analysis Complete")
                        st.code(final_answer, language="text")

                    elif status == "rejected":
                        st.error("❌ File Validation Failed")
                        st.markdown(final_answer)

                    elif status == "failed":
                        st.warning("⚠️ Analysis Could Not Be Completed")
                        st.markdown(final_answer)

                    else:
                        st.info(f"Status: {status}")
                        st.markdown(final_answer)

                    # Show retry info
                    if retry_count > 0:
                        st.info(
                            f"🔄 Agent self-corrected **{retry_count}** time(s) "
                            f"before producing this result."
                        )

                else:
                    st.error(
                        f"Server error (HTTP {response.status_code}): "
                        f"{response.text[:300]}"
                    )

            except requests.ConnectionError:
                st.error(
                    "🔌 Cannot connect to the backend. "
                    "Make sure the API is running on http://localhost:8000"
                )
            except requests.Timeout:
                st.warning(
                    "⏱️ The request timed out. The analysis may be taking longer "
                    "than expected. Please try again."
                )
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")

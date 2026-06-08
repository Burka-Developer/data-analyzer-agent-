"""
File utility helpers for saving uploads, parsing spreadsheets,
deleting temp files, and generating schema summaries for the LLM.
"""

import os
import uuid
import pandas as pd


def save_upload(file_bytes: bytes, original_filename: str, uploads_dir: str = "./uploads") -> str:
    """
    Save uploaded file bytes to ./uploads/{uuid}_{filename}.
    Returns the absolute path to the saved file.
    """
    os.makedirs(uploads_dir, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex[:8]}_{original_filename}"
    file_path = os.path.join(uploads_dir, unique_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    return os.path.abspath(file_path)


def parse_file(file_path: str) -> pd.DataFrame:
    """
    Parse a CSV or Excel file into a pandas DataFrame.
    Raises ValueError if the extension is unsupported or parsing fails.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path)
    elif ext in (".xlsx", ".xls"):
        return pd.read_excel(file_path, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def delete_file(file_path: str) -> None:
    """Safely delete a file if it exists."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass  # Best-effort cleanup


def get_schema_summary(df: pd.DataFrame) -> str:
    """
    Generate a concise schema summary of a DataFrame for the LLM.
    Includes: shape, column names + dtypes, and first 3 rows.
    """
    lines = []
    lines.append(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    lines.append("")
    lines.append("Columns and data types:")
    for col in df.columns:
        lines.append(f"  - {col}: {df[col].dtype}")
    lines.append("")
    lines.append("First 3 rows (sample data):")
    lines.append(df.head(3).to_string(index=False))
    return "\n".join(lines)

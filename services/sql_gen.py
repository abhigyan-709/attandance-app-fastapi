# services/sql_gen.py
import os, re
from typing import List, Tuple
import google.generativeai as genai
from models.sql_gen import SQLGenRequest, SQLGenResponse

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SYSTEM_INSTRUCTIONS = """You generate SQL queries from natural language.
Rules:
- Always output a valid SQL query for the specified DIALECT.
- Respect LIMIT/TOP syntax and functions of that dialect.
- If safe_mode=true, generate only SELECT queries. No DDL/DML.
- Format with indentation and aliases.
- If max_rows provided, add LIMIT/TOP accordingly.
- Return output ONLY inside ```sql code fence```.
- After the SQL, output 3-6 bullet notes inside ```notes code fence```.
"""

PROMPT_TEMPLATE = """Dialect: {dialect}

Schema (optional):
{schema}

Natural language task:
{nl}

Constraints:
- Tables: {tables}
- Max rows: {max_rows}
- Safe mode: {safe_mode}

Generate:
- SQL inside ```sql ... ```
- Notes inside ```notes ... ```
"""

def _extract_blocks(text: str) -> Tuple[str, List[str]]:
    sql = ""
    notes: List[str] = []

    m = re.search(r"```sql\s+([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        sql = m.group(1).strip()
    else:
        m2 = re.search(r"```[\w]*\s+([\s\S]*?)```", text)
        sql = m2.group(1).strip() if m2 else text.strip()

    n = re.search(r"```notes\s+([\s\S]*?)```", text, re.IGNORECASE)
    if n:
        raw = n.group(1).strip()
        for line in raw.splitlines():
            line = line.strip("-•* \t")
            if line:
                notes.append(line)

    return sql, notes

def generate_sql(req: SQLGenRequest) -> SQLGenResponse:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTIONS,
    )

    prompt = PROMPT_TEMPLATE.format(
        dialect=req.dialect,
        schema=req.schema or "N/A",
        nl=req.natural_language,
        tables=", ".join(req.tables) if req.tables else "N/A",
        max_rows=req.max_rows or "N/A",
        safe_mode=req.safe_mode,
    )

    resp = model.generate_content(prompt)
    text = resp.text or ""
    sql, notes = _extract_blocks(text)

    return SQLGenResponse(sql=sql, notes=notes)

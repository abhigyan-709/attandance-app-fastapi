# services/diagram_gen.py
import os, re
from typing import List, Tuple
import google.generativeai as genai
from models.diagram_gen import DiagramRequest, DiagramResponse, DiagramSpec

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SYSTEM_INSTRUCTIONS = """You generate diagrams in PlantUML or Mermaid syntax.
Rules:
- Output ONLY one code block:
  - PlantUML → ```plantuml
  - Mermaid → ```mermaid
- After the code block, output a ```notes block with 3–8 concise bullets.
- Respect given nodes, edges, colors, and layout if provided.
- Do not invent extra components beyond description + spec.
- Syntax must be valid PlantUML or Mermaid.
"""

PROMPT_TEMPLATE = """System description:
{desc}

Structured spec:
{spec}

Generate a {style} diagram.
Use layout: {layout}; theme: {theme}.
Include nodes and edges with given attributes if provided.
"""

def _extract_blocks(text: str) -> Tuple[str, List[str]]:
    code, notes = "", []
    m = re.search(r"```(?:mermaid|plantuml)\s+([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        code = m.group(1).strip()
    else:
        m2 = re.search(r"```[\w]*\s+([\s\S]*?)```", text)
        code = m2.group(1).strip() if m2 else text.strip()

    n = re.search(r"```notes\s+([\s\S]*?)```", text, re.IGNORECASE)
    if n:
        for line in n.group(1).strip().splitlines():
            line = line.strip("-*•\t ")
            if line:
                notes.append(line)
    return code, notes

def _default_filename(spec: DiagramSpec) -> str:
    return "diagram.puml" if spec.style == "plantuml" else "diagram.mmd"

# --- NEW: minimal Mermaid cleanup to avoid 11.x parser bombs
_MMD_EMPTY_SUBGRAPH = re.compile(r"\bsubgraph\s+(['\"])\1\s*$", re.IGNORECASE | re.MULTILINE)

def _sanitize_mermaid(code: str, layout: str) -> str:
    code = code.strip()
    # Replace empty subgraph titles: subgraph ""
    code = _MMD_EMPTY_SUBGRAPH.sub("subgraph Group", code)
    # Ensure the diagram actually starts with a graph directive
    if not re.match(r"^\s*graph\s+\w+", code):
        code = f"graph {layout or 'LR'}\n{code}"
    return code

def generate_diagram(req: DiagramRequest) -> DiagramResponse:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTIONS,
    )

    s = req.spec
    prompt = PROMPT_TEMPLATE.format(
        desc=req.description,
        spec=s.model_dump(),
        style=s.style,
        layout=s.layout or "LR",
        theme=s.theme or "default",
    )

    resp = model.generate_content(prompt)
    text = resp.text or ""
    code, notes = _extract_blocks(text)

    # sanitize Mermaid so the client preview doesn't error
    if s.style == "mermaid":
        code = _sanitize_mermaid(code, s.layout or "LR")

    return DiagramResponse(
        code=code,
        notes=notes,
        filename=_default_filename(s)
    )

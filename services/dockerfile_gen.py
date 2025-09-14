# services/dockerfile_gen.py
import os
import re
from typing import List, Tuple
import google.generativeai as genai
from models.dockerfile import DockerfileRequest, DockerfileResponse

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SYSTEM_INSTRUCTIONS = """You generate production-ready Dockerfiles from a structured spec.
Rules:
- Prefer minimal, secure images. Support multistage when requested.
- Respect OS and package manager choices.
- Only install what is required; clean caches.
- Set WORKDIR, copy only necessary files (leverage requirements files before full copy).
- If nonroot_user=true, create and switch to a non-root user.
- If add_healthcheck=true, add a reasonable HEALTHCHECK for the stack.
- Use EXPOSE for provided ports.
- If entrypoint/start_cmd present, use CMD/ENTRYPOINT accordingly.
- Output ONLY a Dockerfile inside a ```dockerfile code fence```.
- After the Dockerfile, list 3-8 bullet notes (no more) inside a ```notes code fence``` explaining choices."""

PROMPT_TEMPLATE = """Project description:
{desc}

Structured spec (JSON-like):
{spec}

Generate:
- A single Dockerfile (```dockerfile ... ```)
- Then short rationale bullets (```notes ... ```).
"""

def _extract_blocks(text: str) -> Tuple[str, List[str]]:
    """
    Parse ```dockerfile ...``` and ```notes ...``` blocks.
    """
    dockerfile = ""
    notes: List[str] = []

    # dockerfile block
    m = re.search(r"```dockerfile\s+([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        dockerfile = m.group(1).strip()
    else:
        # fallback: any fenced code
        m2 = re.search(r"```[\w]*\s+([\s\S]*?)```", text)
        if m2:
            dockerfile = m2.group(1).strip()
        else:
            dockerfile = text.strip()

    # notes block
    n = re.search(r"```notes\s+([\s\S]*?)```", text, re.IGNORECASE)
    if n:
        raw = n.group(1).strip()
        for line in raw.splitlines():
            line = line.strip("-•* \t")
            if line:
                notes.append(line)

    return dockerfile, notes

def generate_dockerfile(req: DockerfileRequest) -> DockerfileResponse:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTIONS,
    )
    prompt = PROMPT_TEMPLATE.format(desc=req.description, spec=req.spec.model_dump())

    resp = model.generate_content(prompt)
    text = resp.text or ""
    dockerfile, notes = _extract_blocks(text)

    # small sanity: ensure it starts with FROM
    if "FROM " not in dockerfile.upper():
        notes.insert(0, "Model did not start with a FROM. Please review output.")
    return DockerfileResponse(dockerfile=dockerfile, notes=notes)

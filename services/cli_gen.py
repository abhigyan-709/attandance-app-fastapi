# services/cli_gen.py
import os
import re
from typing import List, Tuple
import google.generativeai as genai

from models.cli_gen import CLIGenerateRequest, CLIResponse

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SYSTEM_INSTRUCTIONS = """You generate production-ready CLI tools per a structured spec.

Rules:
- Default to Python 'click' when target is python_click; otherwise emit bash or powershell according to target.
- Respect OS constraints (paths, shell, scheduling).
- If common_flags.verbose, implement --verbose; if dry_run, implement --dry-run; if log_file, implement --log-file with a path.
- Implement provided custom_options (infer types: str,int,float,bool,path; respect 'required' or default).
- Fail safely: validate inputs, handle exceptions, and produce clear error messages.
- Avoid destructive actions unless explicitly enabled by flags or confirmations.
- If scheduler info is provided, include a scheduling snippet appropriate for the OS:
  - linux/mac: cron (and optionally a systemd unit template).
  - windows: schtasks example command.
- Emit ONLY these three fenced blocks, in this exact order:
  1) ```<lang>``` (python|bash|powershell) — full CLI source code
  2) ```requirements``` — one requirement per line (python: include click and needed libs; others may be empty or commented)
  3) ```usage``` — quick start, env vars, example invocations, and scheduling snippet if provided.
"""

PROMPT_TEMPLATE = """Description:
{desc}

Structured spec (JSON-like):
{spec}

Generate the three blocks now.
"""

def _extract_blocks(text: str) -> Tuple[str, List[str], str]:
    """
    Returns: (code, requirements_list, usage_text)
    """
    code = ""
    reqs: List[str] = []
    usage = ""

    # code block: prefer language-tagged
    m = re.search(r"```(python|bash|powershell)\s+([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        code = m.group(2).strip()
    else:
        # fallback: any fenced block
        m2 = re.search(r"```[\w]*\s+([\s\S]*?)```", text)
        if m2:
            code = m2.group(1).strip()

    # requirements block
    r = re.search(r"```requirements\s+([\s\S]*?)```", text, re.IGNORECASE)
    if r:
        raw = r.group(1).strip()
        for line in raw.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                reqs.append(line)

    # usage block
    u = re.search(r"```usage\s+([\s\S]*?)```", text, re.IGNORECASE)
    if u:
        usage = u.group(1).strip()

    return code, reqs, usage

def _filename_for_target(target: str, command_name: str) -> str:
    base = command_name or "cli"
    if target == "bash":
        return f"{base}.sh"
    if target == "powershell":
        return f"{base}.ps1"
    return f"{base}.py"

def generate_cli(req: CLIGenerateRequest) -> CLIResponse:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTIONS,
    )

    prompt = PROMPT_TEMPLATE.format(
        desc=req.description,
        spec=req.spec.model_dump()
    )

    resp = model.generate_content(prompt)
    text = resp.text or ""

    code, requirements, usage = _extract_blocks(text)

    notes: List[str] = []
    if not code.strip():
        notes.append("Model did not produce a code block; please retry or refine the description.")

    filename = _filename_for_target(req.spec.target, req.spec.command_name)
    return CLIResponse(code=code, requirements=requirements, usage=usage, notes=notes, filename=filename)

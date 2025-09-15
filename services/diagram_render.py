# services/diagram_render.py
import os
import httpx

KROKI_BASE = os.getenv("KROKI_BASE", "https://kroki.io")

class DiagramRenderError(RuntimeError): ...
    
def render_with_kroki(style: str, fmt: str, code: str) -> bytes:
    """
    Uses Kroki to render Mermaid / PlantUML to SVG or PNG.
    POST content-type text/plain to:
      {KROKI_BASE}/{style}/{fmt}
    """
    url = f"{KROKI_BASE}/{style}/{fmt}"
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    try:
        r = httpx.post(url, content=code.encode("utf-8"), headers=headers, timeout=30)
        if r.status_code != 200:
            raise DiagramRenderError(f"Kroki error {r.status_code}: {r.text[:300]}")
        return r.content
    except httpx.HTTPError as e:
        raise DiagramRenderError(str(e)) from e

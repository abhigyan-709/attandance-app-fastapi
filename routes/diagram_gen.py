from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response
from models.diagram_gen import DiagramRequest, DiagramResponse
from services.diagram_gen import generate_diagram
from services.diagram_render import render_with_kroki
from models.diagram_gen import DiagramRequest, DiagramResponse, DiagramRenderRequest

diagram_router = APIRouter(prefix="/diagram", tags=["Gemini: Diagram"])

@diagram_router.post("/generate", response_model=DiagramResponse)
def gen(req: DiagramRequest):
    try:
        return generate_diagram(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@diagram_router.post("/generate/raw", response_class=PlainTextResponse)
def gen_raw(req: DiagramRequest):
    try:
        res = generate_diagram(req)
        return PlainTextResponse(res.code, media_type="text/plain; charset=utf-8", headers={
            "Content-Disposition": f'attachment; filename="{res.filename}"'
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@diagram_router.post("/render")
def render(req: DiagramRenderRequest):
    try:
        data = render_with_kroki(req.style, req.format, req.code)
        ctype = "image/svg+xml" if req.format == "svg" else "image/png"
        fname = "diagram.svg" if req.format == "svg" else "diagram.png"
        return Response(
            content=data, media_type=ctype,
            headers={"Content-Disposition": f'attachment; filename="{fname}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
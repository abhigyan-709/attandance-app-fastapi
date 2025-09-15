# routes/cicd_gen.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from models.cicd_gen import CICDRequest, CICDResponse
from services.cicd_gen import generate_cicd

cicd_router = APIRouter(prefix="/cicd", tags=["Gemini: CI/CD"])

@cicd_router.post("/generate", response_model=CICDResponse)
def gen(req: CICDRequest):
    try:
        return generate_cicd(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@cicd_router.post("/generate/raw", response_class=PlainTextResponse)
def gen_raw(req: CICDRequest):
    """Returns the pipeline file as text for direct download."""
    try:
        res = generate_cicd(req)
        media = "text/plain; charset=utf-8"
        # if GH Actions, it's YAML
        if res.filename.endswith((".yml", ".yaml")):
            media = "application/yaml; charset=utf-8"
        return PlainTextResponse(res.pipeline, media_type=media, headers={
            "Content-Disposition": f'attachment; filename="{res.filename.split("/")[-1]}"'
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

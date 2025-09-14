# routes/dockerfile.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from models.dockerfile import DockerfileRequest, DockerfileResponse
from services.dockerfile_gen import generate_dockerfile

dockerfile_router = APIRouter(prefix="/dockerfile", tags=["Gemini: Dockerfile"])

@dockerfile_router.post("/generate", response_model=DockerfileResponse)
def gen(req: DockerfileRequest):
    try:
        return generate_dockerfile(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@dockerfile_router.post("/generate/raw", response_class=PlainTextResponse)
def gen_raw(req: DockerfileRequest):
    """
    Returns plain text to simplify 'Download' buttons without client parsing.
    """
    try:
        res = generate_dockerfile(req)
        return PlainTextResponse(res.dockerfile, media_type="text/plain; charset=utf-8", headers={
            "Content-Disposition": 'attachment; filename="Dockerfile"'
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

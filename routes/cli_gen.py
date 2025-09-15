# routes/cli_gen.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from models.cli_gen import CLIGenerateRequest, CLIResponse
from services.cli_gen import generate_cli

cli_router = APIRouter(prefix="/cli", tags=["Gemini: CLI Generator"])

@cli_router.post("/generate", response_model=CLIResponse)
def gen(req: CLIGenerateRequest):
    try:
        return generate_cli(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@cli_router.post("/generate/raw", response_class=PlainTextResponse)
def gen_raw(req: CLIGenerateRequest):
    try:
        res = generate_cli(req)
        return PlainTextResponse(
            res.code,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{res.filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

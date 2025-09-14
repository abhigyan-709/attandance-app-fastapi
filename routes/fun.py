# routes/fun.py
from fastapi import APIRouter, HTTPException
from models.fun import StyleRequest, StyleResponse, ListResponse
from services.fun_text import list_styles, list_decorators, render

fun_router = APIRouter(prefix="/fun", tags=["Fun"])

@fun_router.get("/styles", response_model=ListResponse, summary="List available base styles")
def get_styles():
    return ListResponse(items=list_styles())

@fun_router.get("/decorators", response_model=ListResponse, summary="List available decorators")
def get_decorators():
    return ListResponse(items=list_decorators())

@fun_router.post("/style", response_model=StyleResponse, summary="Render styled text")
def post_style(payload: StyleRequest):
    if len(payload.text) > 5000:
        raise HTTPException(status_code=413, detail="Text too long (max 5000 chars)")
    try:
        styled = render(payload.text, payload.style, payload.decorator or "none")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return StyleResponse(
        text=payload.text,
        styled=styled,
        style=payload.style,
        decorator=payload.decorator or "none",
    )

# routes/sql_gen.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from models.sql_gen import SQLGenRequest, SQLGenResponse
from services.sql_gen import generate_sql

sql_router = APIRouter(prefix="/sql", tags=["Gemini: SQL"])

@sql_router.post("/generate", response_model=SQLGenResponse)
def gen(req: SQLGenRequest):
    try:
        return generate_sql(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@sql_router.post("/generate/raw", response_class=PlainTextResponse)
def gen_raw(req: SQLGenRequest):
    try:
        res = generate_sql(req)
        return PlainTextResponse(
            res.sql,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="query.sql"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

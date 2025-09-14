from fastapi import APIRouter, HTTPException
from models.password import (
    PasswordCheckRequest, PasswordCheckResponse,
    PasswordGenerateRequest, PasswordGenerateResponse
)
from services.strength import analyze_strength
from services.breach import check_breach
from services.generator import generate_password

router = APIRouter(prefix="/api/password", tags=["Password"])

@router.post("/check", response_model=PasswordCheckResponse)
async def check_password(payload: PasswordCheckRequest):
    # DO NOT log the password anywhere
    strength = analyze_strength(payload.password)
    breached, count = await check_breach(payload.password)

    return PasswordCheckResponse(
        strength_score=strength["strength_score"],
        crack_time=strength["crack_time"],
        suggestions=strength["suggestions"],
        breached=breached,
        breach_count=count,
    )

@router.post("/generate", response_model=PasswordGenerateResponse)
def generate(data: PasswordGenerateRequest):
    try:
        pwd = generate_password(
            length=data.length,
            upper=data.include_upper,
            digits=data.include_digits,
            symbols=data.include_symbols,
        )
        return PasswordGenerateResponse(password=pwd)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

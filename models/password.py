from pydantic import BaseModel, Field

class PasswordCheckRequest(BaseModel):
    password: str = Field(min_length=1)

class PasswordCheckResponse(BaseModel):
    strength_score: int         # 0–4
    crack_time: str             # human readable (“centuries”, “3 hours”, …)
    breached: bool
    breach_count: int
    suggestions: list[str]

class PasswordGenerateRequest(BaseModel):
    length: int = Field(ge=8, le=128, default=16)
    include_upper: bool = True
    include_digits: bool = True
    include_symbols: bool = True

class PasswordGenerateResponse(BaseModel):
    password: str

from pydantic import BaseModel

class PasswordCheckRequest(BaseModel):
    password: str

class PasswordCheckResponse(BaseModel):
    strength_score: int        # 0–4 from zxcvbn
    crack_time: str            # human-readable
    breached: bool
    breach_count: int
    suggestions: list[str]

class PasswordGenerateRequest(BaseModel):
    length: int = 16
    include_upper: bool = True
    include_digits: bool = True
    include_symbols: bool = True

class PasswordGenerateResponse(BaseModel):
    password: str

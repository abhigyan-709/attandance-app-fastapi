from zxcvbn import zxcvbn

def analyze_strength(password: str) -> dict:
    res = zxcvbn(password)
    # Fallbacks to keep response stable
    crack = res.get("crack_times_display", {}).get(
        "offline_fast_hashing_1e10_per_second", "unknown"
    )
    fb = res.get("feedback", {}) or {}
    suggestions = fb.get("suggestions") or []
    return {
        "strength_score": int(res.get("score", 0)),
        "crack_time": str(crack),
        "suggestions": [str(s) for s in suggestions],
    }

from zxcvbn import zxcvbn

def analyze_strength(password: str):
    result = zxcvbn(password)
    return {
        "strength_score": result["score"],
        "crack_time": result["crack_times_display"]["offline_fast_hashing_1e10_per_second"],
        "suggestions": result["feedback"]["suggestions"],
    }

import secrets, string

SYMBOLS = "!@#$%^&*()-_=+[]{};:,<.>/?"

def generate_password(length: int, upper=True, digits=True, symbols=True) -> str:
    pool = list(string.ascii_lowercase)
    if upper:
        pool += list(string.ascii_uppercase)
    if digits:
        pool += list(string.digits)
    if symbols:
        pool += list(SYMBOLS)

    if not pool:
        raise ValueError("No character set selected")

    # ensure variety if options selected
    parts = []
    if upper:   parts.append(secrets.choice(string.ascii_uppercase))
    if digits:  parts.append(secrets.choice(string.digits))
    if symbols: parts.append(secrets.choice(SYMBOLS))
    while len(parts) < length:
        parts.append(secrets.choice(pool))
    secrets.SystemRandom().shuffle(parts)
    return "".join(parts[:length])

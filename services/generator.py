import secrets, string

def generate_password(length: int, upper=True, digits=True, symbols=True):
    chars = list(string.ascii_lowercase)
    if upper: chars.extend(string.ascii_uppercase)
    if digits: chars.extend(string.digits)
    if symbols: chars.extend("!@#$%^&*()-_=+[]{};:,.<>?/")

    if not chars:
        raise ValueError("No character set selected")

    return "".join(secrets.choice(chars) for _ in range(length))

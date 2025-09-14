import hashlib, httpx

API_URL = "https://api.pwnedpasswords.com/range/"

async def check_breach(password: str):
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    async with httpx.AsyncClient() as client:
        r = await client.get(API_URL + prefix)
        if r.status_code != 200:
            return False, 0

    matches = [line.split(":") for line in r.text.splitlines()]
    for s, count in matches:
        if s == suffix:
            return True, int(count)

    return False, 0

import hashlib
import httpx
import time

API_URL = "https://api.pwnedpasswords.com/range/"
UA = "ProjectDevOpsTools/1.0 (contact: connect@projectdevops.in)"  # required by HIBP

async def check_breach(password: str) -> tuple[bool, int]:
    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    # polite client with retries for 429/5xx
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={
                "User-Agent": UA,
                "Add-Padding": "true",  # privacy
            }) as client:
                r = await client.get(API_URL + prefix)
            if r.status_code == 200:
                for line in r.text.splitlines():
                    sfx, count = line.split(":")
                    if sfx == suffix:
                        return True, int(count)
                return False, 0
            if r.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            # any other error -> treat as “not breached” but safe default
            return False, 0
        except httpx.HTTPError:
            time.sleep(0.6 * (attempt + 1))
            continue
    return False, 0

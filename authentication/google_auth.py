from google.oauth2 import id_token
from google.auth.transport import requests
from authentication.secrets import get_google_oauth_secrets

def verify_google_token(id_token_str: str) -> dict | None:
    secrets = get_google_oauth_secrets()
    client_id = secrets.get("GOOGLE_ANDROID_CLIENT_ID")

    try:
        id_info = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            client_id
        )

        # ID token is valid. Return the payload.
        return {
            "sub": id_info["sub"],  # Unique Google user ID
            "email": id_info.get("email"),
            "name": id_info.get("name"),
            "picture": id_info.get("picture"),
        }
    except Exception as e:
        print(f"Invalid Google ID token: {e}")
        return None

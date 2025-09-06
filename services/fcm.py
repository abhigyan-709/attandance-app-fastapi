# services/fcm.py
import json
import os
from typing import List, Dict, Any

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]
_FCM_V1_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"


def _load_sa_credentials():
    """
    Load service-account credentials from either:
      - FIREBASE_SA_PATH (path to JSON file inside container), or
      - FIREBASE_SA_JSON (raw JSON string in env var).
    """
    sa_path = os.getenv("FIREBASE_SA_PATH")
    sa_json = os.getenv("FIREBASE_SA_JSON")

    if sa_path and os.path.exists(sa_path):
        with open(sa_path, "r", encoding="utf-8") as f:
            info = json.load(f)
    elif sa_json:
        info = json.loads(sa_json)
    else:
        raise RuntimeError("Missing service account: set FIREBASE_SA_PATH or FIREBASE_SA_JSON")

    return service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)


def _get_access_token(creds):
    """
    Get an OAuth2 access token for the FCM scope.
    """
    creds = creds.with_scopes(_SCOPES)
    creds.refresh(Request())
    return creds.token


def send_fcm(tokens: List[str], title: str, body: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Send push notifications via FCM HTTP v1.
    We send one HTTP call per token (simple & reliable).
    """
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    if not project_id:
        raise RuntimeError("FIREBASE_PROJECT_ID not set")

    creds = _load_sa_credentials()
    access_token = _get_access_token(creds)

    url = _FCM_V1_URL.format(project_id=project_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    results = []
    # v1 supports topic/condition too; here we fan out per token
    for t in tokens:
        payload = {
            "message": {
                "token": t,
                "notification": {"title": title, "body": body},
                # FCM v1 expects all data values to be strings
                "data": {k: str(v) for k, v in (data or {}).items()},
                "android": {"priority": "HIGH"},
                "apns": {"headers": {"apns-priority": "10"}},
                "webpush": {"headers": {"Urgency": "high"}},
            }
        }
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        try:
            results.append(r.json())
        except Exception:
            results.append({"status_code": r.status_code, "text": r.text})

    return results

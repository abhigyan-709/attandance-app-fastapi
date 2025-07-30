import boto3
import json
from botocore.exceptions import ClientError

def get_secret_value(secret_name: str, region="ap-south-1") -> dict:
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response.get("SecretString")
        return json.loads(secret_string) if secret_string else {}
    except ClientError as e:
        print(f"Error fetching secret {secret_name}: {e}")
        return {}

def get_google_access_secret() -> str:
    data = get_secret_value("google_access_secret")
    return data.get("ACCESS_SECRET_KEY", "fallback-access-secret")

def get_google_refresh_secret() -> str:
    data = get_secret_value("google_refresh_secret")
    return data.get("REFRESH_SECRET_KEY", "fallback-refresh-secret")

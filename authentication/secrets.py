import boto3
import json
from botocore.exceptions import ClientError

def get_google_oauth_secrets(secret_name="google_oauth_secret", region="ap-south-1"):
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret_data = response.get("SecretString")
        return json.loads(secret_data) if secret_data else {}
    except ClientError as e:
        print(f"Error fetching Google OAuth secrets: {e}")
        return {}

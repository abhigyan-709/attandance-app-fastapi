# import boto3
# import json

# # Initialize the Secrets Manager client
# client = boto3.client('secretsmanager', region_name='ap-south-1')  # Replace 'us-west-2' with your region

# # Function to get the secret from Secrets Manager
# def get_mongo_uri():
#     secret_name = "my_mongo_secret"  # Replace with your secret name
#     try:
#         # Retrieve the secret value
#         response = client.get_secret_value(SecretId=secret_name)
        
#         # If the secret is in the 'SecretString' field
#         if 'SecretString' in response:
#             secret = json.loads(response['SecretString'])
#             return secret["MONGO_URI"]
#         else:
#             # If the secret is binary, decode it
#             decoded_binary_secret = response['SecretBinary']
#             return decoded_binary_secret
#     except Exception as e:
#         print(f"Error retrieving secret: {e}")
#         return None
    
# # removed unused secret

# # Get Mongo URI from Secrets Manager
# mongo_uri = get_mongo_uri()

# # Now use the Mongo URI to connect to MongoDB
# from pymongo import MongoClient

# if mongo_uri:
#     client = MongoClient(mongo_uri)
#     print(client)
#     print("Successfully connected to MongoDB!")
# else:
#     print("Failed to retrieve Mongo URI.")


import boto3
import json
import redis

def get_redis_credentials():
    """Fetch Redis credentials from AWS Secrets Manager."""
    secret_name = "RedisCredentials"  # Change to your secret name
    region_name = "ap-south-1"  # e.g., "us-east-1"

    client = boto3.client("secretsmanager", region_name=region_name)
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        return secret
    except Exception as e:
        print(f"Error fetching Redis credentials: {e}")
        return None

# Load Redis credentials
secrets = get_redis_credentials()
if secrets:
    REDIS_HOST = secrets["REDIS_HOST"]
    REDIS_PORT = int(secrets["REDIS_PORT"])
    REDIS_PASSWORD = secrets["REDIS_PASSWORD"]
else:
    raise Exception("Could not retrieve Redis credentials.")

# Connect to Redis
redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True
)
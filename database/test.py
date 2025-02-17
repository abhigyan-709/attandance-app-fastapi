import boto3
import json

# Initialize the Secrets Manager client
client = boto3.client('secretsmanager', region_name='ap-south-1')  # Replace 'us-west-2' with your region

# Function to get the secret from Secrets Manager
def get_mongo_uri():
    secret_name = "my_mongo_secret"  # Replace with your secret name
    try:
        # Retrieve the secret value
        response = client.get_secret_value(SecretId=secret_name)
        
        # If the secret is in the 'SecretString' field
        if 'SecretString' in response:
            secret = json.loads(response['SecretString'])
            return secret["MONGO_URI"]
        else:
            # If the secret is binary, decode it
            decoded_binary_secret = response['SecretBinary']
            return decoded_binary_secret
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return None

# Get Mongo URI from Secrets Manager
mongo_uri = get_mongo_uri()

# Now use the Mongo URI to connect to MongoDB
from pymongo import MongoClient

if mongo_uri:
    client = MongoClient(mongo_uri)
    print(client)
    print("Successfully connected to MongoDB!")
else:
    print("Failed to retrieve Mongo URI.")

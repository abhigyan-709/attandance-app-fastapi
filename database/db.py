import boto3
import json
from pymongo import MongoClient
from botocore.exceptions import ClientError

class Database:
    client: MongoClient = None
    db_name: str = "testdb"
    secret_name = "my_mongo_secret"  # Replace with your AWS Secret name

    #get mongodb uri
    def get_mongo_uri(self):
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name="ap-south-1")  # Replace with your region

        try:
            # Retrieve the secret value
            response = client.get_secret_value(SecretId=self.secret_name)

            # Check if the secret is in string format or binary
            if 'SecretString' in response:
                secret = json.loads(response['SecretString'])
                return secret["MONGO_URI"]  # Ensure the key matches your secret structure
            else:
                # If the secret is binary, decode it
                decoded_binary_secret = response['SecretBinary']
                return decoded_binary_secret
        except ClientError as e:
            print(f"Error retrieving secret: {e}")
            return None

    def connect(self):
        # Retrieve the Mongo URI from AWS Secrets Manager
        mongo_uri = self.get_mongo_uri()

        if mongo_uri:
            print(f"Connecting to MongoDB using URI: {mongo_uri}")
            self.client = MongoClient(mongo_uri)
        else:
            print("Failed to retrieve Mongo URI from Secrets Manager.")

    def get_client(self) -> MongoClient:
        if not self.client:
            self.connect()
        return self.client

# Example usage
db = Database()
client = db.get_client()

import boto3
import json
from pymongo import MongoClient
from botocore.exceptions import ClientError

class Database:
    client: MongoClient = None
    db_name: str = "testdb"
    secret_name = "my_mongo_secret"  # Replace with your AWS Secret name

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


# import boto3
# import json
# import redis
# from pymongo import MongoClient
# from botocore.exceptions import ClientError

# class Database:
#     client: MongoClient = None
#     redis_client: redis.Redis = None
#     db_name: str = "testdb"
#     secret_name = "my_mongo_secret"  # Replace with your AWS Secret name
#     redis_host = "13.233.112.149"  # Replace with your Redis server IP
#     redis_port = 6379

#     def test_connections(self):
#     # Check Redis connection
#         try:
#             redis_ping = self.redis_client.ping()
#             print(f"Redis connected: {redis_ping}")
#         except redis.ConnectionError as e:
#             print(f"Error connecting to Redis: {e}")
        
#         # Check MongoDB connection
#         try:
#             self.client.server_info()  # Tries to get server info from MongoDB
#             print("MongoDB connected successfully!")
#         except Exception as e:
#             print(f"Error connecting to MongoDB: {e}")

#     def get_mongo_uri(self):
#         session = boto3.session.Session()
#         client = session.client(service_name="secretsmanager", region_name="ap-south-1")

#         try:
#             response = client.get_secret_value(SecretId=self.secret_name)

#             if 'SecretString' in response:
#                 secret = json.loads(response['SecretString'])
#                 return secret["MONGO_URI"]
#             else:
#                 return response['SecretBinary']
#         except ClientError as e:
#             print(f"Error retrieving secret: {e}")
#             return None

#     def connect(self):
#         mongo_uri = self.get_mongo_uri()

#         if mongo_uri:
#             print(f"Connecting to MongoDB using URI: {mongo_uri}")
#             self.client = MongoClient(mongo_uri)
#         else:
#             print("Failed to retrieve Mongo URI from Secrets Manager.")

#         # Connect to Redis
#         self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port, db=0, decode_responses=True)

#     def get_client(self) -> MongoClient:
#         if not self.client:
#             self.connect()
#         return self.client

#     def get_redis(self) -> redis.Redis:
#         if not self.redis_client:
#             self.connect()
#         return self.redis_client

# # Example usage
# db = Database()
# client = db.get_client()
# redis_client = db.get_redis()
# db.test_connections() 

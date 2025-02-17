# from pymongo import MongoClient
# import os
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# class Database:
#     client: MongoClient = None
#     db_name: str = "testdb"

#     def connect(self):
#         mongo_uri = os.environ.get("MONGO_URI")
#         print(mongo_uri)
#         if not mongo_uri:
#             raise ValueError("MONGO_URI is not set in the environment variables.")
#         self.client = MongoClient(mongo_uri)

#     def get_client(self) -> MongoClient:
#         if not self.client:
#             self.connect()
#         return self.client

# db = Database()


from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Database:
    client: MongoClient = None
    db_name: str = "testdb"

    def connect(self):
        # Use the same credentials as in the mongosh command
        mongo_uri = "mongodb://admin:projectdevops709@13.233.112.149:27017/admin?authSource=admin"
        print(f"Connecting to MongoDB using URI: {mongo_uri}")
        self.client = MongoClient(mongo_uri)

    def get_client(self) -> MongoClient:
        if not self.client:
            self.connect()
        return self.client

# Example usage
db = Database()


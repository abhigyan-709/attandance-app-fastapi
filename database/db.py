import os
from pymongo import MongoClient

class Database:
    client: MongoClient = None
    db_name: str = "testdb"
    def get_mongo_uri(self):
        return os.getenv("MONGO_URI")

    def connect(self):
        # Retrieve the Mongo URI from environment
        mongo_uri = self.get_mongo_uri()

        if mongo_uri:
            print(f"Connecting to MongoDB using URI: {mongo_uri}")
            self.client = MongoClient(mongo_uri)
        else:
            print("Failed to retrieve Mongo URI from environment.")

    def get_client(self) -> MongoClient:
        if not self.client:
            self.connect()
        return self.client

# Example usage
db = Database()
client = db.get_client()

# Helper function for background scheduler
def get_mongo_uri():
    """Get MongoDB URI for background tasks"""
    return db.get_mongo_uri()

import os
from pymongo import MongoClient

MONGO_URL = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/mydatabase")  # Use Docker service name
client = MongoClient(MONGO_URL)
db = client["attendance_db"]

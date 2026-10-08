import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import Config

# Module-level client and database instances
_client = None
_db = None

def get_db():
    """
    Returns the MongoDB database instance.
    Reuses the client connection pool for efficiency.
    """
    global _client, _db
    if _db is None:
        try:
            _client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=4000)
            # Ping database to verify connection
            _client.admin.command('ping')
            _db = _client[Config.DATABASE_NAME]
            print(f"[MongoDB] Successfully connected to database: '{Config.DATABASE_NAME}'")
        except (ConnectionFailure, ServerSelectionTimeoutError) as err:
            print(f"[MongoDB Connection Error] Failed to connect to MongoDB at {Config.MONGO_URI}: {err}", file=sys.stderr)
            raise err
    return _db

def close_db():
    """Closes the MongoDB connection pool if open."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        print("[MongoDB] Connection closed.")

"""TinyDB helper layer – extend as needed."""
from tinydb import TinyDB

def get_db(path: str = "tracker_db.json") -> TinyDB:
    return TinyDB(path)
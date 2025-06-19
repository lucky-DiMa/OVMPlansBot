from pymongo import MongoClient, ReturnDocument
from config import MONGO_AUTH_LINK, MONGO_CLUSTER_NAME

mongo_db = MongoClient(MONGO_AUTH_LINK)[MONGO_CLUSTER_NAME]


def get_next_id(collection_name: str) -> int:
    return mongo_db['Counters'].find_one_and_update({"_id": collection_name}, {"$inc": {"count": 1}},
                                                    return_document=ReturnDocument.AFTER,
                                                    upsert=True,
                                                    projection={'_id': False, 'count': True})["count"]

from typing import ClassVar

from pymongo.collection import Collection

from classes.json_serializable_object import JsonSerializableObject
from classes.classproperty import classproperty
from utils import mongo_db


class MongoDBObject(JsonSerializableObject):
    collection_name: ClassVar[str]

    @classproperty
    def collection(cls) -> Collection:
        return mongo_db[cls.collection_name]
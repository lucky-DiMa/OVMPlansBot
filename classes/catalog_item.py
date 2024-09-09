from __future__ import annotations
import pymongo
from classes import PlansBotUser
from classes.actions import SendMessageAction
from typing import List, Any

from mongo_connector import mongo_db, get_next_id


class CatalogItem:
    collection = mongo_db['CatalogItems']

    def __init__(self, _id: int, text: str, prev_catalog_item_text: str, index: int, actions_ids: List[int] | list | None = None):
        if actions_ids is None:
            actions_ids = []
        self.__id = _id
        self.__index = index
        self.__text = text
        self.__prev_catalog_item_text = prev_catalog_item_text
        self.__actions_ids = actions_ids

    @property
    def id(self) -> int:
        return self.__id

    @property
    def text(self) -> str:
        return self.__text

    @property
    def index(self) -> int:
        return self.__index

    @property
    def prev_catalog_item_text(self) -> str:
        return self.__prev_catalog_item_text

    @property
    def actions_ids(self) -> List[int] | list:
        return self.__actions_ids

    @property
    def actions(self) -> List[SendMessageAction] | list:
        return SendMessageAction.get_list_by_ids(self.actions_ids)

    @classmethod
    def from_JSON(cls, json: dict | None) -> CatalogItem | None:
        if json is None:
            return None
        return cls(json['_id'], json["text"], json["prev_catalog_item_text"], json["index"], json["actions_ids"])

    @text.setter
    def text(self, _text: str) -> None:
        self.collection.update_one({'text': self.__text}, {'$set': {'text': _text}})
        self.__text = _text

    @index.setter
    def index(self, _index: int) -> None:
        self.collection.update_one({'text': self.__text}, {'$set': {'index': _index}})
        self.__index = _index

    def to_JSON(self) -> dict:
        return {'_id': self.__id,
                'text': self.__text,
                'index': self.__index,
                'prev_catalog_item_text': self.__prev_catalog_item_text,
                "actions_ids": self.__actions_ids}

    @classmethod
    def get_by_text(cls, text: str) -> CatalogItem:
        return cls.from_JSON(cls.collection.find_one({'text': text}))

    @classmethod
    def create(cls, text: str | None = None, prev_catalog_item_text: str = 'main') -> CatalogItem:
        next_id = cls.next_id()
        next_index = cls.get_next_index_by_prev_catalog_item_text("main")
        if text is None:
            text = f'ЭЛЕМЕНТ {next_id}'
        return cls.get_by_id(cls.collection.insert_one(cls(next_id, text, prev_catalog_item_text, next_index, []).to_JSON()).inserted_id)

    @classmethod
    def get_by_prev_catalog_item_text(cls, prev_catalog_item_text: str) -> List[CatalogItem] | list:
        return list(map(cls.from_JSON, list(cls.collection.find({'prev_catalog_item_text': prev_catalog_item_text}).sort([('index', pymongo.ASCENDING)]))))

    @property
    def new_keyboard(self) -> list | List[CatalogItem]:
        return self.__class__.get_by_prev_catalog_item_text(self.text)

    @classmethod
    def next_id(cls) -> int:
        return get_next_id(cls.collection.name)

    @classmethod
    def get_by_id(cls, _id: int) -> CatalogItem:
        return cls.from_JSON(cls.collection.find_one({"_id": _id}))

    def add_action(self, action_id: int) -> None:
        self.__actions_ids.append(action_id)
        self.set_field("actions_ids", self.__actions_ids)

    def remove_action_by_id(self, action_id: int) -> None:
        self.__actions_ids.remove(action_id)
        self.set_field("actions_ids", self.__actions_ids)

    def remove_action_by_index(self, action_i: int) -> None:
        self.__actions_ids.pop(action_i)
        self.set_field("actions_ids", self.__actions_ids)

    def swap_actions_by_ids(self, id1: int, id2: int) -> None:
        self.swap_actions_by_indexes(self.__actions_ids.index(id1), self.__actions_ids.index(id2))

    def swap_actions_by_indexes(self, i1: int, i2: int) -> None:
        (self.__actions_ids[i1],
         self.__actions_ids[i2]) = (self.__actions_ids[i2],
                                    self.__actions_ids[i1])
        self.set_field("actions_ids", self.__actions_ids)

    def set_field(self, field_name: str, value: Any) -> None:
        self.__class__.set_field_by_id(self.id, field_name, value)

    @classmethod
    def set_field_by_id(cls, _id: int , field_name: str, value: Any) -> None:
        cls.collection.update_one({"_id": _id}, {"$set": {field_name: value}})

    async def process_tap(self, user: PlansBotUser) -> None:
        for action in self.actions:
            await action.process(user)

    def delete(self) -> None:
        self.__class__.delete_by_id(self.id, self)

    @classmethod
    def delete_by_id(cls, _id: int, obj: CatalogItem | None = None) -> None:
        if not obj:
            obj = cls.get_by_id(_id)
        for action in obj.actions:
            action.delete()
        for catalog_item_json in cls.collection.find({"index": {"$gt": cls.from_JSON(cls.collection.find_one_and_delete({'_id': _id})).index}}):
            cls.from_JSON(catalog_item_json).index = cls.from_JSON(catalog_item_json).index - 1

    @classmethod
    def get_count_by_prev_catalog_item_text(cls, prev_catalog_item_text: str) -> int:
        return len(cls.get_by_prev_catalog_item_text(prev_catalog_item_text))


    @classmethod
    def get_next_index_by_prev_catalog_item_text(cls, prev_catalog_item_text: str) -> int:
        return cls.get_count_by_prev_catalog_item_text(prev_catalog_item_text) + 1

    @classmethod
    def reorder_catalog_items_by_prev_catalog_item_text(cls, order: List[int], prev_catalog_item_text: str) -> bool:
        if len(order) != cls.get_count_by_prev_catalog_item_text(prev_catalog_item_text):
            return False
        for i, _id in enumerate(order):
            cls.set_field_by_id(_id, "index", i + 1)
        return True


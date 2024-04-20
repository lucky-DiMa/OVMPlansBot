from __future__ import annotations

from classes import PlansBotUser
from classes.actions import SendMessageAction
from typing import List, Any

from mongo_connector import mongo_db, get_next_id


class CatalogItem:
    collection = mongo_db['Catalog Items']

    def __init__(self, _id: int, text: str, prev_catalog_item_text: str, actions_ids: List[int] | list | None = None):
        if actions_ids is None:
            actions = []
        self.__id = _id
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
        return cls(json['_id'], json["text"], json["prev_catalog_item_text"], json["actions_ids"])

    @text.setter
    def text(self, _text: str):
        self.collection.update_one({'text': self.__text}, {'$set': {'text': _text}})
        self.__text = _text

    def to_JSON(self) -> dict:
        return {'_id': self.__id,
                'text': self.__text,
                'prev_catalog_item_text': self.__prev_catalog_item_text,
                "actions_ids": self.__actions_ids}

    @classmethod
    def get_by_text(cls, text: str) -> CatalogItem:
        return cls.from_JSON(cls.collection.find_one({'text': text}))

    @classmethod
    def create(cls, text: str, prev_catalog_item_text: str) -> CatalogItem:
        return cls.get_by_id(cls.collection.insert_one(cls(cls.next_id(), text, prev_catalog_item_text, []).to_JSON()).inserted_id)

    @classmethod
    def get_by_prev_catalog_item_text(cls, prev_catalog_item_text: str) -> List[CatalogItem] | list:
        return list(map(cls.from_JSON, list(cls.collection.find({'prev_catalog_item_text': prev_catalog_item_text}))))

    @property
    def new_keyboard(self) -> list | List[CatalogItem]:
        return self.__class__.get_by_prev_catalog_item_text(self.text)

    @classmethod
    def next_id(cls) -> int:
        return get_next_id(cls.collection.name)

    @classmethod
    def get_by_id(cls, _id: int):
        return cls.from_JSON(cls.collection.find_one({"_id": _id}))

    def add_action(self, action_id: int) -> None:
        self.__actions_ids.append(action_id)
        self.__set_field("actions_ids", self.__actions_ids)

    def remove_action_by_id(self, action_id: int) -> None:
        self.__actions_ids.remove(action_id)
        self.__set_field("actions_ids", self.__actions_ids)

    def remove_action_by_index(self, action_i: int) -> None:
        self.__actions_ids.pop(action_i)
        self.__set_field("actions_ids", self.__actions_ids)

    def swap_actions_by_ids(self, id1: int, id2: int) -> None:
        self.swap_actions_by_indexes(self.__actions_ids.index(id1), self.__actions_ids.index(id2))

    def swap_actions_by_indexes(self, i1: int, i2: int) -> None:
        (self.__actions_ids[i1],
         self.__actions_ids[i2]) = (self.__actions_ids[i2],
                                    self.__actions_ids[i1])
        self.__set_field("actions_ids", self.__actions_ids)

    def __set_field(self, field_name: str, value: Any) -> None:
        self.__class__.collection.update_one({"_id": self.id}, {"$set": {field_name: value}})

    async def process_tap(self, user: PlansBotUser):
        for action in self.actions:
            await action.process(user)

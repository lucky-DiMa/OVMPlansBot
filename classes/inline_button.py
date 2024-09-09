from __future__ import annotations

from enum import Enum
from typing import Any, List

from aiogram.filters.callback_data import CallbackData

from classes import PlansBotUser
from mongo_connector import mongo_db, get_next_id


class ButtonCallbackData(CallbackData, prefix='button'):
    button_id: int


class InlineButtonType(Enum):
    link = 'link'
    callback = 'callback'


class InlineButton:
    collection = mongo_db['Inline buttons']

    def __init__(self, _id: int, text: str, actions_ids: List[int] | list | None = None, link: str | None = None):
        if actions_ids is None:
            actions_ids = []
        self.__id = _id
        self.__text = text
        self.__actions_ids = actions_ids
        self.__link = link

    @property
    def id(self) -> int:
        return self.__id

    @property
    def text(self) -> str:
        return self.__text

    @property
    def actions_ids(self) -> List[int] | list:
        return self.__actions_ids

    @property
    def actions(self):
        from classes.actions import SendMessageAction
        return SendMessageAction.get_list_by_ids(self.actions_ids)

    @property
    def link(self) -> str:
        return self.__link

    @text.setter
    def text(self, _text: str) -> None:
        self.__set_field('text', _text)
        self.__text = _text

    @link.setter
    def link(self, link: str) -> None:
        self.__set_field('link', link)
        self.__link = link

    @property
    def type(self) -> InlineButtonType:
        return InlineButtonType.link if self.link is not None else InlineButtonType.callback

    def add_action(self, action_id: int) -> None:
        self.__actions_ids.append(action_id)
        self.__set_field("actions_ids", self.__actions_ids)

    def remove_action_by_id(self, action_id: int) -> None:
        self.__actions_ids.remove(action_id)
        self.__set_field("action_ids", self.__actions_ids)

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

    @classmethod
    def next_id(cls) -> int:
        return get_next_id(cls.collection.name)

    @classmethod
    def create(cls, text: str) -> InlineButton:
        return cls.get_by_id(cls.collection.insert_one(cls(cls.next_id(), text).to_JSON()).inserted_id)

    @classmethod
    def get_by_id(cls, _id: int) -> InlineButton:
        return cls.from_JSON(cls.collection.find_one({"_id": _id}))

    def to_JSON(self) -> dict:
        return {"_id": self.id, "text": self.text, "actions_ids": self.actions_ids, "link": self.link}

    @classmethod
    def from_JSON(cls, json: dict) -> InlineButton | None:
        if json is None:
            return None
        return cls(json["_id"], json["text"], json["actions_ids"], json["link"])

    @classmethod
    def get_list_by_ids(cls, ids: List[int] | list) -> List[InlineButton] | list:
        if not ids:
            return []
        return list(map(cls.from_JSON, list(cls.collection.find({"_id": {'$in': ids}}))))

    async def process_tap(self, user: PlansBotUser) -> None:
        for action in self.actions:
            await action.process(user)

    def delete(self):
        for action in self.actions:
            action.delete()
        self.__class__.delete_by_id(self.id)

    @classmethod
    def delete_by_id(cls, _id: int):
        cls.collection.delete_one({'_id': _id})


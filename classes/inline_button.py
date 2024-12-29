from __future__ import annotations

from typing import Any, List, Literal

from aiogram.filters.callback_data import CallbackData

from classes import PlansBotUser
from mongo_connector import mongo_db, get_next_id


class ButtonCallbackData(CallbackData, prefix='button'):
    button_id: int


class InlineButton:
    collection_name = 'Inline buttons'
    collection = mongo_db[collection_name]
    fields = ["_id", "text", "type", "actions_ids", "link"]

    def __init__(self, _id: int, text: str, type_: Literal["link", "callback"], actions_ids: List[int] | list | None = None, link: str | None = None):
        if actions_ids is None:
            actions_ids = []
        self._id = _id
        self._text = text
        self._type = type_
        self._actions_ids = actions_ids
        self._link = link

    @property
    def id(self) -> int:
        return self._id

    @property
    def text(self) -> str:
        return self._text

    @property
    def actions_ids(self) -> List[int] | list:
        return self._actions_ids

    @property
    def actions(self):
        from classes.actions import SendMessageAction
        return SendMessageAction.get_list_by_ids(self.actions_ids)

    @property
    def link(self) -> str:
        return self._link

    @text.setter
    def text(self, _text: str) -> None:
        self.__set_field('text', _text)
        self._text = _text

    @link.setter
    def link(self, link: str) -> None:
        self.__set_field('link', link)
        self._link = link

    @property
    def type(self) -> str:
        return self._type

    def add_action(self, action_id: int) -> None:
        self._actions_ids.append(action_id)
        self.__set_field("actions_ids", self._actions_ids)

    def remove_action_by_id(self, action_id: int) -> None:
        self._actions_ids.remove(action_id)
        self.__set_field("action_ids", self._actions_ids)

    def remove_action_by_index(self, action_i: int) -> None:
        self._actions_ids.pop(action_i)
        self.__set_field("actions_ids", self._actions_ids)

    def swap_actions_by_ids(self, id1: int, id2: int) -> None:
        self.swap_actions_by_indexes(self._actions_ids.index(id1), self._actions_ids.index(id2))

    def swap_actions_by_indexes(self, i1: int, i2: int) -> None:
        (self._actions_ids[i1],
         self._actions_ids[i2]) = (self._actions_ids[i2],
                                   self._actions_ids[i1])
        self.__set_field("actions_ids", self._actions_ids)

    def __set_field(self, field_name: str, value: Any) -> None:
        self.__class__.__set_field_by_id(self.id, field_name, value)

    @classmethod
    def __set_field_by_id(cls, _id: int, field_name: Any, value: Any):
        cls.collection.update_one({"_id": _id}, {"$set": {field_name: value}})

    @classmethod
    def next_id(cls) -> int:
        return get_next_id(cls.collection.name)

    @classmethod
    def create(cls, text: str, type_: Literal["link", "callback"]) -> InlineButton:
        return cls.get_by_id(cls.collection.insert_one(cls(cls.next_id(), text, type_).to_JSON()).inserted_id)

    @classmethod
    def get_by_id(cls, _id: int) -> InlineButton:
        return cls.from_JSON(cls.collection.find_one({"_id": _id}))

    def to_JSON(self, extend: bool = False) -> dict:
        if extend:
            res = self.to_JSON()
            res["actions"] = list(map(lambda action: action.to_JSON(), self.actions))
            return res
        return {field: self.__getattribute__(field) for field in self.__class__.fields}

    @classmethod
    def from_JSON(cls, data: dict) -> InlineButton | None:
        if data is None:
            return None
        return cls(*[data[field] for field in cls.fields])

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

    def reorder_actions(self, actions_ids: List[int]):
        self._actions_ids = actions_ids
        self.__set_field("actions_ids", actions_ids)

    @classmethod
    def get_by_containing_action_id(cls, _id: int):
        return cls.from_JSON(cls.collection.find_one({"actions_ids": _id}))

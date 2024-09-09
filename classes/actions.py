from __future__ import annotations

from typing import List, Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from classes import PlansBotUser
from classes.inline_button import InlineButton, InlineButtonType, ButtonCallbackData
from classes.keyboard_types import KeyboardType
from mongo_connector import mongo_db, get_next_id


class SendMessageAction:
    collection = mongo_db["Actions"]

    def __init__(self, _id: int,
                 message_text: str,
                 with_keyboard: bool = False,
                 inline_buttons_ids: List[int] | None = None):
        if inline_buttons_ids is None:
            inline_buttons_ids = []
        self.__id = _id
        self.__message_text = message_text
        self.__with_keyboard = with_keyboard
        self.__inline_buttons_ids = inline_buttons_ids

    @classmethod
    def next_id(cls) -> int:
        return get_next_id(cls.collection.name)

    @property
    def id(self) -> int:
        return self.__id

    @property
    def message_text(self) -> str:
        return self.__message_text

    @property
    def with_keyboard(self) -> bool:
        return self.__with_keyboard

    @property
    def keyboard(self) -> List[InlineButton] | list:
        return InlineButton.get_list_by_ids(self.inline_buttons_ids)

    @property
    def inline_keyboard_markup(self):
        kb = self.keyboard
        if not kb:
            return None
        builder = InlineKeyboardBuilder()
        for button in kb:
            if button.type == InlineButtonType.link:
                builder.button(text=button.text, url=button.link)
            else:
                builder.button(text=button.text, callback_data=ButtonCallbackData(button_id=button.id).pack())
        builder.adjust(2, repeat=True)
        return builder.as_markup()


    @property
    def inline_buttons_ids(self) -> List[int] | list:
        return self.__inline_buttons_ids

    @message_text.setter
    def message_text(self, message_text: str):
        self.collection.update_one({'_id': self.id}, {'$set': {'message_text': message_text}})
        self.__message_text = message_text

    @with_keyboard.setter
    def with_keyboard(self, with_keyboard: bool):
        self.collection.update_one({'_id': self.id}, {'$set': {'with_keyboard': with_keyboard}})
        self.__with_keyboard = with_keyboard

    def __set_field(self, field_name: str, value: Any) -> None:
        self.__class__.collection.update_one({"_id": self.id}, {"$set": {field_name: value}})

    def enable_keyboard(self, first_button_id: int) -> None:
        self.with_keyboard = True
        self.__inline_buttons_ids = [first_button_id]
        self.__set_field("inline_buttons_ids", self.__inline_buttons_ids)

    def disable_keyboard(self) -> None:
        self.with_keyboard = False
        self.__inline_buttons_ids = []
        self.__set_field("inline_buttons_ids", self.__inline_buttons_ids)

    def add_inline_button(self, inline_button_id: int) -> None:
        self.__inline_buttons_ids.append(inline_button_id)
        self.__set_field("inline_buttons_ids", self.__inline_buttons_ids)

    def remove_inline_button_by_id(self, inline_button_id: int) -> None:
        self.__inline_buttons_ids.remove(inline_button_id)
        self.__set_field("inline_buttons_ids", self.__inline_buttons_ids)

    def remove_inline_button_by_index(self, inline_button_i: int) -> None:
        self.__inline_buttons_ids.pop(inline_button_i)
        self.__set_field("inline_buttons_ids", self.__inline_buttons_ids)

    def swap_inline_buttons_by_ids(self, id1: int, id2: int) -> None:
        self.swap_inline_buttons_by_indexes(self.__inline_buttons_ids.index(id1), self.__inline_buttons_ids.index(id2))

    def swap_inline_buttons_by_indexes(self, i1: int, i2: int) -> None:
        (self.__inline_buttons_ids[i1],
         self.__inline_buttons_ids[i2]) = (self.__inline_buttons_ids[i2],
                                           self.__inline_buttons_ids[i1])
        self.__set_field("inline_buttons_ids", self.__inline_buttons_ids)

    def to_JSON(self) -> dict:
        return {'_id': self.id,
                "type": 'send_message',
                "message_text": self.message_text,
                "with_keyboard": self.with_keyboard,
                "inline_buttons_ids": self.inline_buttons_ids}

    @classmethod
    def from_JSON(cls, json: dict | None) -> SendMessageAction | None:
        if json is None:
            return None
        return cls(json['_id'],
                   json['message_text'],
                   json['with_keyboard'],
                   json['inline_buttons_ids'])

    @classmethod
    def create(cls, message_text: str) -> SendMessageAction:
        return cls.get_by_id(cls.collection.insert_one(cls(cls.next_id(), message_text).to_JSON()).inserted_id)

    @classmethod
    def get_by_id(cls, _id: int) -> SendMessageAction:
        return cls.from_JSON(cls.collection.find_one({"_id": _id}))

    @classmethod
    def get_list_by_ids(cls, ids: List[int] | list) -> List[SendMessageAction] | list:
        if not ids:
            return []
        return list(map(cls.from_JSON, list(cls.collection.find({"_id": {'$in': ids}}))))

    async def process(self, user: PlansBotUser) -> None:
        if not self.with_keyboard:
            await user.send_message(self.message_text)
        else:
            await user.send_message(self.message_text, markup=self.inline_keyboard_markup)

    def delete(self):
        self.__class__.delete_by_id(self.id, self)

    @classmethod
    def delete_by_id(cls, _id: int, obj: SendMessageAction | None = None) -> None:
        if not obj:
            obj = cls.get_by_id(_id)
        for button in obj.keyboard:
            button.delete()
        cls.collection.delete_one({'_id': _id})

    def set_field(self, field_name: str, value: Any) -> None:
        self.__class__.set_field_by_id(self.id, field_name, value)

    @classmethod
    def set_field_by_id(cls, _id: int, field_name: str, value: Any) -> None:
        cls.collection.update_one({"_id": _id}, {"$set": {field_name: value}})


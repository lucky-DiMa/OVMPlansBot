from __future__ import annotations

from typing import List

from mongo_connector import mongo_db


class CatalogItem:
    collection = mongo_db['Catalog Items']

    def __init__(self, text: str, prev_catalog_item_text: str, message_text: str, message_photo_id: str | None):
        self.__message_photo_id = message_photo_id
        self.__prev_catalog_item_text = prev_catalog_item_text
        self.__text = text
        self.__message_text = message_text

    @property
    def text(self) -> str:
        return self.__text

    @property
    def prev_catalog_item_text(self) -> str:
        return self.__prev_catalog_item_text

    @property
    def message_text(self) -> str:
        return self.__message_text

    @property
    def message_photo_id(self) -> str:
        return self.__message_photo_id

    @classmethod
    def from_JSON(cls, json: dict | None) -> CatalogItem | None:
        if json is None:
            return None
        return cls(json["text"], json["prev_catalog_item_text"], json["message_text"], json["message_photo_id"])

    @text.setter
    def text(self, _text: str):
        self.collection.update_one({'text': self.__text}, {'$set': {'text': _text}})
        self.__text = _text

    @message_text.setter
    def message_text(self, _message_text: str):
        self.collection.update_one({'text': self.__text}, {'$set': {'message_text': _message_text}})
        self.__text = _message_text

    @message_photo_id.setter
    def message_photo_id(self, _message_photo_id: str):
        self.collection.update_one({'text': self.__text}, {'$set': {'message_photo_id': _message_photo_id}})
        self.__text = _message_photo_id

    def to_JSON(self) -> dict:
        return {'message_text': self.__message_text,
                'message_photo_id': self.__message_photo_id,
                'text': self.__text,
                'prev_catalog_item_text': self.__prev_catalog_item_text}

    @classmethod
    def get_by_text(cls, text: str) -> CatalogItem:
        return cls.from_JSON(cls.collection.find_one({'text': text}))

    @classmethod
    def create(cls, text: str, prev_catalog_item_text: str, message_text: str, message_photo_id: str | None = None) -> CatalogItem:
        item = cls(text, prev_catalog_item_text, message_text, message_photo_id)
        cls.collection.insert_one(item.to_JSON())
        return item

    @classmethod
    def get_by_prev_catalog_item_text(cls, prev_catalog_item_text: str) -> List[CatalogItem] | list:
        return [cls.from_JSON(_dict) for _dict in cls.collection.find({'prev_catalog_item_text': prev_catalog_item_text})]

    @property
    def new_keyboard(self) -> list | List[CatalogItem]:
        return self.__class__.get_by_prev_catalog_item_text(self.text)

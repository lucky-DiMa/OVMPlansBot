from __future__ import annotations
from typing import NamedTuple, List
from mongo_connector import mongo_db
import secrets

from mytime import now_time


class SuccessfulCreatedSession(NamedTuple):
    access_token: str
    session: Session


class Session:
    collection_name = "Sessions"
    collection = mongo_db[collection_name]

    def __init__(self, token: str, telegram_id: int, name: str):
        self.__name = name
        self.__token = token
        self.__telegram_id = telegram_id

    @property
    def token(self):
        return self.__token

    @property
    def telegram_id(self):
        return self.__telegram_id

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name_: str):
        self.__name = name_
        self.__class__.collection.update_one({'token': self.__token}, {'$set': {'name': self.__name}})

    @classmethod
    def from_JSON(cls, json: dict):
        if json is None:
            return None
        return cls(json["token"], json["telegram_id"], json["name"])

    @classmethod
    def get_by_token(cls, token: str) -> Session:
        return cls.from_JSON(cls.collection.find_one({"token": token}))

    @classmethod
    def get_by_telegram_id(cls, telegram_id: int) -> List[Session] | list:
        return cls.from_JSON_list(list(cls.collection.find({"telegram_id": telegram_id})))

    @classmethod
    def create(cls, telegram_id: int) -> Session:
        token = secrets.token_urlsafe(16)
        while cls.get_by_token(token) is not None:
            token = secrets.token_urlsafe(16)
        session = Session(token, telegram_id, f'Новая сессия от {now_time()}')
        cls.collection.insert_one(session.to_JSON())
        return session

    def to_JSON(self) -> dict:
        return {"token": self.token, "telegram_id": self.telegram_id, "name": self.name}

    @classmethod
    def from_JSON_list(cls, list_: List[dict] | list) -> List[Session] | list:
        result_list = []
        for json in list_:
            result_list.append(cls.from_JSON(json))
        return result_list

    def end(self):
        self.__class__.end_by_token(self.token)

    @classmethod
    def end_by_token(cls, token: str):
        cls.collection.delete_one({'token': token})

    @classmethod
    def end_all_by_telegram_id(cls, telegram_id: int):
        cls.collection.delete_many({'telegram_id': telegram_id})

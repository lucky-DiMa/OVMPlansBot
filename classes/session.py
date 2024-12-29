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
    fields = ["token", "csrf_token", "telegram_id", "name"]

    def __init__(self, token: str, csrf_token: str, telegram_id: int, name: str):
        self._csrf_token = csrf_token
        self._name = name
        self._token = token
        self._telegram_id = telegram_id

    @property
    def token(self) -> str:
        return self._token

    @property
    def csrf_token(self) -> str:
        return self._csrf_token

    @property
    def telegram_id(self) -> int:
        return self._telegram_id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name
        self.__class__.collection.update_one({'token': self._token}, {'$set': {'name': self._name}})

    @classmethod
    def from_JSON(cls, data: dict | None) -> Session | None:
        if data is None:
            return None
        return cls(*[data[field] for field in cls.fields])

    @classmethod
    def get_by_token(cls, token: str) -> Session:
        return cls.from_JSON(cls.collection.find_one({"token": token}))

    @classmethod
    def __get_by_csrf_token(cls, csrf_token: str) -> Session | None:
        return cls.from_JSON(cls.collection.find_one({"csrf_token": csrf_token}))

    @classmethod
    def get_by_telegram_id(cls, telegram_id: int) -> List[Session] | list:
        return cls.from_JSON_list(list(cls.collection.find({"telegram_id": telegram_id})))

    @classmethod
    def create(cls, telegram_id: int) -> Session:
        token = secrets.token_urlsafe(16)
        while cls.get_by_token(token) is not None:
            token = secrets.token_urlsafe(16)
        csrf_token = secrets.token_urlsafe(16)
        while cls.__get_by_csrf_token(csrf_token) is not None:
            csrf_token = secrets.token_urlsafe(16)
        session = Session(token, csrf_token, telegram_id, f'Новая сессия от {now_time()}')
        cls.collection.insert_one(session.to_JSON())
        return session

    def to_JSON(self) -> dict:
        return {field: self.__getattribute__(field) for field in self.__class__.fields}

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

from copy import copy
from typing import List

from aiogram import types

from classes.mongo_db_object import MongoDBObject
from utils import mongo_db


class Email(MongoDBObject):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    collection_name = 'emails'
    fields = {'address': str,
              "send_all": bool,
              'location': str}

    def __init__(self, address: str, send_all: bool,
                 locations: List[str]):
        self._send_all = send_all
        self._address = address
        self._locations = locations

    @property
    def send_all(self):
        return self._send_all

    @property
    def address(self):
        return self._address

    @property
    def locations(self):
        return self._locations

    @address.setter
    def address(self, address: str):
        if self.__class__.exists(address):
            return
        self.collection.update_one({"address": self.address}, {"$set": {"address": address}})
        self._address = address

    @send_all.setter
    def send_all(self, send_all: bool):
        if self.send_all == send_all:
            return
        if send_all:
            self.collection.update_one({"address": self.address}, {"$set": {"locations": mongo_db["Locations"].find_one({})["list"]}})
            self._locations = mongo_db["Locations"].find_one({})["list"]
        if not send_all:
            self._locations = []
            self.collection.update_one({"address": self.address}, {"$set": {"locations": []}})
        self.set_send_all(send_all)

    def set_send_all(self, send_all: bool):
        self._send_all = send_all
        self.collection.update_one({"address": self.address}, {"$set": {"send_all": send_all}})

    @property
    def editing_text(self):
        return f'Адрес: {self.address}'

    @property
    def editing_markup(self):
        markup = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=f'{"✅" if self.send_all else "🔲"}Выбрать все регионы', callback_data=f'SET SEND_ALL {"FALSE" if self.send_all else "TRUE"}')], *[[types.InlineKeyboardButton(text=f'{"✅" if location in self.locations else "🔲"} {location}', callback_data=f'{"ADD" if location not in self.locations else "REMOVE"} LOCATION - {location}')] for location in mongo_db["Locations"].find_one({})["list"]],[types.InlineKeyboardButton(text='Удалить', callback_data='DELETE EMAIL')], [types.InlineKeyboardButton(text='Завершить редактирование', callback_data='END EDITING EMAIL')]])
        # markup.add(types.InlineKeyboardButton(text='Изменить адрес', callback_data='CHANGE ADDRESS'))
        # for location in mongo_db["Locations"].find_one({})["list"]:
        #     markup.add(types.InlineKeyboardButton(text=f'{"✅" if location in self.locations else "🔲"} {location}', callback_data=f'{"ADD" if location not in self.locations else "REMOVE"} LOCATION - {location}'))
        # markup.add(types.InlineKeyboardButton(text='Удалить', callback_data='DELETE EMAIL'))
        # markup.add(types.InlineKeyboardButton(text='Завершить редактирование', callback_data='END EDITING EMAIL'))
        return markup

    def add_location(self, location: str):
        new_locations = copy(self.locations)
        new_locations.append(location)
        self.collection.update_one({"address": self.address}, {"$set": {"locations": new_locations}})
        self._locations = new_locations

    def remove_location(self, location: str):
        self.set_send_all(False)
        new_locations = copy(self.locations)
        new_locations.remove(location)
        self.collection.update_one({"address": self.address}, {"$set": {"locations": new_locations}})
        self._locations = new_locations

    @classmethod
    def exists(cls, address: str):
        return cls.collection.find_one({"address": address}) is not None

    @classmethod
    def add(cls, address: str):
        if cls.exists(address):
            return None
        new_mail = cls(address, False, [])
        cls.collection.insert_one(new_mail.to_json())
        return new_mail

    @classmethod
    def get_all(cls):
        results = []
        for e_dict in cls.collection.find({}):
            results.append(cls.from_json(e_dict))
        return results

    @classmethod
    def delete_by_address(cls, address: str):
        cls.collection.delete_one({"address": address})

    def delete(self):
        self.__class__.delete_by_address(self.address)

    @classmethod
    def get_by_address(cls, address: str):
        if not cls.exists(address):
            return None
        return cls.from_json(cls.collection.find_one({"address": address}))

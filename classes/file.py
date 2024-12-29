from __future__ import annotations

import os
from typing import List

from aiogram.types import FSInputFile, InputMediaAudio, InputMediaPhoto, InputMediaVideo, InputMediaDocument

from mongo_connector import mongo_db, get_next_id


class File:
    collection_name = "Files"
    collection = mongo_db[collection_name]
    fields = ["_id", "type", "extension", "name"]

    def __init__(self, _id: int,
                 type_: str,
                 extension: str,
                 name: str):
        self._id = _id
        self._type = type_
        self._extension = extension
        self._name = name

    @property
    def id(self) -> int:
        return self._id

    @property
    def type(self) -> str:
        return self._type

    @property
    def extension(self) -> str:
        return self._extension

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return f"./static/uploaded_files/{self._id}.{self._extension}"

    @classmethod
    def get_files_list(cls, ids: List[int] | list) -> List[int] | list:
        if not ids:
            return []
        unsorted_list = list(map(cls.from_JSON, list(cls.collection.find({"_id": {'$in': ids}}))))
        dict_by_ids = {action.id: action for action in unsorted_list}
        return list(map(lambda id_: dict_by_ids[id_], ids))

    @classmethod
    def from_JSON(cls, data: dict | None) -> File | None:
        if data is None:
            return None
        return cls(*[data[field] for field in cls.fields])

    def to_JSON(self, extend: bool = False) -> dict:
        if extend:
            res = self.to_JSON()
            res["path"] = self.path
            return res
        return {field: self.__getattribute__(field) for field in self.__class__.fields}

    @classmethod
    def create(cls,  type_: str, extension: str, name: str) -> File:
        file = cls(cls.next_id(), type_, extension, name)
        cls.collection.insert_one(file.to_JSON())
        return file

    @classmethod
    def next_id(cls) -> int:
        return get_next_id(cls.collection.name)

    def delete(self) -> None:
        self.__class__.delete_by_id(self.id, self)

    @classmethod
    def delete_by_id(cls, _id: int, obj: File | None = None) -> None:
        if not obj:
            obj = cls.get_by_id(_id)
        os.remove(obj.path)
        from classes import SendMessageAction
        SendMessageAction.get_by_containing_file_id(_id).remove_file_by_id(_id)
        cls.collection.delete_one({"_id": _id})

    @classmethod
    def get_by_id(cls, _id: int) -> File | None:
        return cls.from_JSON(cls.collection.find_one({"_id": _id}))

    def to_fs_input_file(self) -> FSInputFile:
        return FSInputFile(self.path, self.name)

    def to_input_media(self) -> InputMediaAudio | InputMediaPhoto | InputMediaVideo | InputMediaDocument:
        match self.type:
            case "audio":
                return InputMediaDocument(media=self.to_fs_input_file())
            case "image":
                return InputMediaPhoto(media=self.to_fs_input_file())
            case "video":
                return InputMediaVideo(media=self.to_fs_input_file())
            case _:
                return InputMediaDocument(media=self.to_fs_input_file())


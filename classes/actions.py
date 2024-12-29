from __future__ import annotations

from classes.file import File
from typing import List, Any

from aiogram.types import InlineKeyboardMarkup, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder

from classes import PlansBotUser
from classes.inline_button import InlineButton, ButtonCallbackData
from mongo_connector import mongo_db, get_next_id


class SendMessageAction:
    collection_name = "Actions"
    collection = mongo_db[collection_name]
    fields = ["_id", "message_text", "files_ids", "with_keyboard", "inline_buttons_ids"]

    def __init__(self, _id: int,
                 message_text: str,
                 files_ids: List[int] | None = None,
                 with_keyboard: bool = False,
                 inline_buttons_ids: List[int] | None = None):
        if files_ids is None:
            files_ids = []
        if inline_buttons_ids is None:
            inline_buttons_ids = []
        self._id = _id
        self._message_text = message_text
        self._files_ids = files_ids
        self._with_keyboard = with_keyboard
        self._inline_buttons_ids = inline_buttons_ids

    @classmethod
    def next_id(cls) -> int:
        return get_next_id(cls.collection.name)

    @property
    def id(self) -> int:
        return self._id

    @property
    def message_text(self) -> str:
        return self._message_text

    @property
    def files_ids(self) -> List[int] | list:
        return self._files_ids

    @property
    def files(self) -> List[File] | list:
        return File.get_files_list(self.files_ids)

    @property
    def with_keyboard(self) -> bool:
        return self._with_keyboard

    @property
    def keyboard(self) -> List[InlineButton] | list:
        return InlineButton.get_list_by_ids(self.inline_buttons_ids)

    @property
    def inline_keyboard_markup(self) -> InlineKeyboardMarkup | None:
        kb = self.keyboard
        if not kb:
            return None
        builder = InlineKeyboardBuilder()
        for button in kb:
            if button.type == "link":
                builder.button(text=button.text, url=button.link)
            else:
                builder.button(text=button.text, callback_data=ButtonCallbackData(button_id=button.id).pack())
        builder.adjust(2, repeat=True)
        return builder.as_markup()

    @property
    def inline_buttons_ids(self) -> List[int] | list:
        return self._inline_buttons_ids

    @message_text.setter
    def message_text(self, message_text: str):
        self.collection.update_one({'_id': self.id}, {'$set': {'message_text': message_text}})
        self._message_text = message_text

    @with_keyboard.setter
    def with_keyboard(self, with_keyboard: bool):
        self.collection.update_one({'_id': self.id}, {'$set': {'with_keyboard': with_keyboard}})
        self._with_keyboard = with_keyboard

    def enable_keyboard(self, first_button_id: int) -> None:
        self.with_keyboard = True
        self._inline_buttons_ids = [first_button_id]
        self.__set_field("inline_buttons_ids", self._inline_buttons_ids)

    def disable_keyboard(self) -> None:
        self.with_keyboard = False
        self._inline_buttons_ids = []
        self.__set_field("inline_buttons_ids", self._inline_buttons_ids)

    def add_inline_button(self, inline_button_id: int) -> None:
        self._inline_buttons_ids.append(inline_button_id)
        self.__set_field("inline_buttons_ids", self._inline_buttons_ids)

    def add_file(self, file_id: int) -> None:
        self._files_ids.append(file_id)
        self.__set_field("files_ids", self._files_ids)

    def remove_inline_button_by_id(self, inline_button_id: int) -> None:
        self._inline_buttons_ids.remove(inline_button_id)
        self.__set_field("inline_buttons_ids", self._inline_buttons_ids)

    def remove_inline_button_by_index(self, inline_button_i: int) -> None:
        self._inline_buttons_ids.pop(inline_button_i)
        self.__set_field("inline_buttons_ids", self._inline_buttons_ids)

    def remove_file_by_id(self, file_id: int) -> None:
        self._files_ids.remove(file_id)
        self.__set_field("files_ids", self._files_ids)

    def remove_file_by_index(self, file_i: int) -> None:
        self._files_ids.pop(file_i)
        self.__set_field("files_ids", self._files_ids)

    def swap_inline_buttons_by_ids(self, id1: int, id2: int) -> None:
        self.swap_inline_buttons_by_indexes(self._inline_buttons_ids.index(id1), self._inline_buttons_ids.index(id2))

    def swap_inline_buttons_by_indexes(self, i1: int, i2: int) -> None:
        (self._inline_buttons_ids[i1],
         self._inline_buttons_ids[i2]) = (self._inline_buttons_ids[i2],
                                          self._inline_buttons_ids[i1])
        self.__set_field("inline_buttons_ids", self._inline_buttons_ids)

    def to_JSON(self, extend: bool = False) -> dict:
        if extend:
            res = self.to_JSON()
            res["files"] = list(map(lambda file: file.to_JSON(True), self.files))
            res["keyboard"] = list(map(lambda inline_button: inline_button.to_JSON(), self.keyboard))
            return res
        return {"type": "send_message", **{field: self.__getattribute__(field) for field in self.__class__.fields}}

    @classmethod
    def from_JSON(cls, data: dict | None) -> SendMessageAction | None:
        if data is None:
            return None
        return cls(*[data[field] for field in cls.fields])

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
        unsorted_list = list(map(cls.from_JSON, list(cls.collection.find({"_id": {'$in': ids}}))))
        dict_by_ids = {action.id: action for action in unsorted_list}
        return list(map(lambda id_: dict_by_ids[id_], ids))

    async def process(self, user: PlansBotUser) -> None:
        files = self.files
        if files:
            if len(files) == 1:
                match files[0].type:
                    case 'image':
                        await user.send_photo(files[0].to_fs_input_file(), self.message_text, reply_markup=self.inline_keyboard_markup)
                    case 'video':
                        await user.send_video(files[0].to_fs_input_file(), self.message_text, reply_markup=self.inline_keyboard_markup)
                    case 'audio':
                        await user.send_audio(files[0].to_fs_input_file(), self.message_text, reply_markup=self.inline_keyboard_markup)
                    case _:
                        await user.send_document(files[0].to_fs_input_file(), self.message_text, reply_markup=self.inline_keyboard_markup)
            else:
                media_group = [file.to_input_media() for file in self.files]
                media_group[-1].caption = self.message_text
                await user.send_media_group(media_group)

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
        for file in obj.files:
            file.delete()
        from classes import CatalogItem
        c_i = CatalogItem.get_by_containing_action_id(_id)
        i_b = InlineButton.get_by_containing_action_id(_id)
        if c_i:
            c_i.remove_action_by_id(_id)
        if i_b:
            i_b.remove_action_by_id(_id)
        cls.collection.delete_one({'_id': _id})

    def __set_field(self, field_name: str, value: Any) -> None:
        self.__class__.__set_field_by_id(self.id, field_name, value)

    @classmethod
    def __set_field_by_id(cls, _id: int, field_name: str, value: Any) -> None:
        cls.collection.update_one({"_id": _id}, {"$set": {field_name: value}})

    def reorder_files(self, files_ids: List[int]):
        self._files_ids = files_ids
        self.__set_field("files_ids", files_ids)

    @classmethod
    def get_by_containing_file_id(cls, file_id: int):
        return cls.from_JSON(cls.collection.find_one({"files_ids": file_id}))

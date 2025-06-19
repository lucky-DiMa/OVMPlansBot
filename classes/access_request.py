from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import Any, List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from classes import PlansBotUser
from classes.mongo_db_object import MongoDBObject
from classes.plans_bot_user import PermissionDeniedException
from bot.create_bot import bot
from utils import mongo_db, get_next_id, now_time, beauty_datetime


class AccessRequestStatuses(Enum):
    waiting = 'ожидание'
    canceled = 'отменён'
    accepted = 'принят'
    rejected = 'отклонён'
    rejected_and_banned = 'отклонён и заблокирован'


class ModifyException(Exception):
    """You cannot modify this request now"""


class ResponseException(Exception):
    """You cannot respond this request now"""


class RequestNotFoundException(Exception):
    """Request with given ID not found"""


class CancelException(Exception):
    """You cannot cancel this request now"""


class AccessRequest(MongoDBObject):
    collection_name = 'AccessRequests'
    fields = {'user_id': int,
              'user_fullname': str,
              'user_location': str,
              'user_section': str,
              'status': str,
              'date': datetime,
              'last_modify_datetime': datetime,
              'responder_id': int, 'responder_fullname': str}
    
    def __init__(self, _id: int, user_id: int,
                 user_fullname: str,
                 user_location: str,
                 user_section: str, 
                 status: str,
                 creation_datetime: datetime,
                 last_modify_datetime: datetime = None,
                 response_datetime: datetime = None,
                 admin_id: int = None,
                 admin_fullname: str = None):
        self.__id = _id
        self.__user_id = user_id
        self.__user_fullname = user_fullname
        self.__user_location = user_location
        self.__user_section = user_section
        self.__status = status
        self.__creation_datetime = creation_datetime
        self.__last_modify_datetime = last_modify_datetime
        self.__response_datetime =  response_datetime
        self.__responder_id = admin_id
        self.__responder_fullname = admin_fullname

    @staticmethod
    def editing_keyboard():
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Изменить ФИО', callback_data='EDIT REG FULLNAME')],
                                         [InlineKeyboardButton(text='Изменить регион', callback_data='EDIT REG LOCATION')],
                                         [InlineKeyboardButton(text='Изменить отдел', callback_data='EDIT REG SECTION')],
                                         [InlineKeyboardButton(text='Отозвать запрос', callback_data='CANCEL REG')]])

    def responding_keyboard(self):
        if self.able_to_response_to:
            return InlineKeyboardMarkup(inline_keyboard=[
                                   [InlineKeyboardButton(text='Принять', callback_data=f'ACCEPT REG {self.id}'),
                                    InlineKeyboardButton(text='Отклонить',  callback_data=f'REJECT REG {self.id}')],
                                   [InlineKeyboardButton(text=f'Заблокировать {self.user_fullname}',
                                                               callback_data=f'REJECT AND BAN REG {self.id}')],
                                   [InlineKeyboardButton(text='↻ Обновить',
                                                               callback_data=f'VIEW REQUEST {self.id}')],
                                   [InlineKeyboardButton(text="<< Назад >>", callback_data='UPDATE REQUESTS')]])
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="<< Назад >>", callback_data='UPDATE REQUESTS')]])

    @classmethod
    def set_field_by_id(cls, _id: int, field: str, value: Any):
        cls.collection.update_one({'_id': _id}, {'$set': {field: value}})

    def set_field(self, field: str, value: Any):
        self.__class__.set_field_by_id(self.__id, field, value)

    @property
    def id(self):
        return self.__id

    @property
    def user_id(self):
        return self.__user_id

    @property
    def user_fullname(self):
        return self.__user_fullname

    @property
    def user_location(self):
        return self.__user_location

    @property
    def user_section(self):
        return self.__user_section

    @property
    def status(self):
        return self.__status

    @property
    def creation_datetime(self):
        return self.__creation_datetime

    @property
    def last_modify_datetime(self):
        return self.__last_modify_datetime

    @property
    def response_datetime(self):
        return self.__response_datetime

    @property
    def responder_id(self):
        return self.__responder_id

    @property
    def responder_fullname(self):
        return self.__responder_fullname

    @user_fullname.setter
    def user_fullname(self, new_user_fullname: str):
        if not self.able_to_modify:
            raise ModifyException()
        self.update_last_modify_datetime()
        self.__user_fullname = new_user_fullname
        self.set_field('user_fullname', new_user_fullname)

    @user_location.setter
    def user_location(self, new_user_location: str):
        if not self.able_to_modify:
            raise ModifyException()
        self.update_last_modify_datetime()
        self.__user_location = new_user_location
        self.set_field('user_location', new_user_location)

    @user_section.setter
    def user_section(self, new_user_section: str):
        if not self.able_to_modify:
            raise ModifyException()
        self.update_last_modify_datetime()
        self.__user_section = new_user_section
        self.set_field('user_section', new_user_section)

    def update_last_modify_datetime(self):
        if not self.able_to_modify:
            raise ModifyException()
        self.set_field('last_modify_datetime', now_time())

    def accept(self, responder_id: int):
        if not self.able_to_response_to:
            raise ResponseException()
        responder = PlansBotUser.get_by_id(responder_id)
        if not responder.is_owner:
            if not responder.is_admin:
                raise PermissionDeniedException(
                    f'User: "{responder.fullname}" {responder.id}. Permission: choose_admins. Reason: user is not admin.')
            if not responder.is_allowed('responder'):
                raise PermissionDeniedException(
                    f'User: "{responder.fullname}" {responder.id}. Permission: responder. Reason: user is admin but has not this permission')
        self.__status = AccessRequestStatuses.accepted.name
        self.set_field('status', self.__status)
        now_time_ = now_time()
        self.__response_datetime = now_time_
        self.set_field('response_datetime', now_time_)
        self.__responder_id = responder.id
        self.set_field('responder_id', responder_id)
        self.__responder_fullname = responder.fullname
        self.set_field('responder_fullname', responder.fullname)
        PlansBotUser.get_by_id(self.__user_id).state = "NONE"

    def reject(self, responder_id: int):
        if not self.able_to_response_to:
            raise ResponseException()
        responder = PlansBotUser.get_by_id(responder_id)
        if not responder.is_owner:
            if not responder.is_admin:
                raise PermissionDeniedException(
                    f'User: "{responder.fullname}" {responder.id}. Permission: choose_admins. Reason: user is not admin.')
            if not responder.is_allowed('responder'):
                raise PermissionDeniedException(
                    f'User: "{responder.fullname}" {responder.id}. Permission: responder. Reason: user is admin but has not this permission')
        self.__status = AccessRequestStatuses.rejected.name
        self.set_field('status', self.__status)
        now_time_ = now_time()
        self.__response_datetime = now_time_
        self.set_field('response_datetime', now_time_)
        self.__responder_id = responder.id
        self.set_field('responder_id', responder_id)
        self.__responder_fullname = responder.fullname
        self.set_field('responder_fullname', responder.fullname)
        PlansBotUser.delete_by_id(self.__user_id)

    def reject_and_ban(self, responder_id: int):
        if not self.able_to_response_to:
            raise ResponseException()
        responder = PlansBotUser.get_by_id(responder_id)
        if not responder.is_owner:
            if not responder.is_admin:
                raise PermissionDeniedException(
                    f'User: "{responder.fullname}" {responder.id}. Permission: choose_admins. Reason: user is not admin.')
            if not responder.is_allowed('responder'):
                raise PermissionDeniedException(
                    f'User: "{responder.fullname}" {responder.id}. Permission: responder. Reason: user is admin but has not this permission')
        self.__status = AccessRequestStatuses.rejected_and_banned.name
        self.set_field('status', self.__status)
        now_time_ = now_time()
        self.__response_datetime = now_time_
        self.set_field('response_datetime', now_time_)
        self.__responder_id = responder.id
        self.set_field('responder_id', responder_id)
        self.__responder_fullname = responder.fullname
        self.set_field('responder_fullname', responder.fullname)
        PlansBotUser.ban_by_id(self.__user_id)

    def cancel(self):
        if not self.able_to_response_to:
            raise CancelException()
        self.__status = AccessRequestStatuses.canceled.name
        self.set_field('status', self.__status)
        now_time_ = now_time()
        self.__response_datetime = now_time_
        self.set_field('response_datetime', now_time_)
        PlansBotUser.delete_by_id(self.__user_id)

    @classmethod
    def get_by_id(cls, _id: int):
        data = cls.collection.find_one({'_id': _id})
        if not data:
            raise RequestNotFoundException(f"Given ID: {_id}")
        return cls.from_json(data)

    @classmethod
    def get_all(cls) -> List[AccessRequest] | list:
        return list(map(cls.from_json, cls.collection.find()))

    @classmethod
    def get_waiting(cls) -> List[AccessRequest] | list:
        return list(map(cls.from_json, cls.collection.find({"status": AccessRequestStatuses.waiting.name})))

    @classmethod
    def get_waiting_by_user_id(cls, user_id: int) -> AccessRequest | None:
        return cls.from_json(cls.collection.find_one({"user_id": user_id, "status": AccessRequestStatuses.waiting.name}))

    # @classmethod
    # def get_latest_by_user_id(cls, user_id: int) -> AccessRequest | None:
    #     ODO find latest request by user_id
    #     ...

    @classmethod
    def next_id(cls) -> int:
        return get_next_id(cls.collection.name)

    @classmethod
    def create(cls, user: PlansBotUser) -> AccessRequest:
        request = AccessRequest(cls.next_id(), user.id, user.fullname, user.location, user.section, AccessRequestStatuses.waiting.name, now_time())
        cls.collection.insert_one(request.to_json())
        return request

    @property
    def able_to_response_to(self) -> bool:
        return self.status == AccessRequestStatuses.waiting.name

    @property
    def able_to_modify(self) -> bool:
        return self.status == AccessRequestStatuses.waiting.name

    async def get_info(self, for_sender: bool):
        resp =  ("Запрос на получение доступа к боту был отправлен!\n\n" if for_sender else "") + f'Запрос <u><i>#{self.id}</i></u>:\nУказанное ФИО: <code>{self.user_fullname}</code>\nВыбранный регион: <code>{self.user_location}</code>\nВыбранный отдел: <code>{self.user_section}</code>\nИнформация об аккаунте в Telegram:\nID: <code>{self.user_id}</code>\nПолное имя: <code>{(await bot.get_chat(self.__user_id)).full_name}</code>\nUsername: {"@" + (await bot.get_chat(self.__user_id)).username if (await bot.get_chat(self.__user_id)).username else "<code>не указан</code>"}\n\nВремя создания запроса: <code>{beauty_datetime(self.__creation_datetime, 1)}</code>\nВремя последнего изменения: <code>{beauty_datetime(self.__last_modify_datetime, 1) if self.__last_modify_datetime else "запрос не был изменён"}</code>\n\nСтатус: <code>{AccessRequestStatuses.__getitem__(self.status).value}</code>'
        if not self.able_to_response_to:
            if self.status == AccessRequestStatuses.canceled.name:
                resp += '\nВремя отмены: <code>' + beauty_datetime(self.__response_datetime, 1) + '</code>'
            else:
                resp += '\nВремя ответа: <code>' + beauty_datetime(self.__response_datetime, 1) + '</code>'
                resp += f'\n\nАдминистратор, ответивший на запрос:\nID: <code>{self.__responder_id}</code>\nФИО: <code>{self.__responder_fullname}</code>'
        return resp

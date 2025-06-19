from __future__ import annotations
from datetime import date

from bot.admin_permission import permissions
from bot.create_bot import bot
from utils import mongo_db
from aiogram import types
from typing import NamedTuple, Any, List


class IsEditingResult(NamedTuple):
    is_editing: bool
    who_is_editing: PlansBotUser | None


class UserNotFoundException(Exception):
    """User with given id not found"""


class AlreadyDoneException(Exception):
    """Action already done"""


class AdminAlreadyPromotedException(AlreadyDoneException):
    """User already is admin"""


class AdminAlreadyDismissedException(AlreadyDoneException):
    """User already is not admin"""


class PermissionDeniedException(Exception):
    """Permission denied"""


class UserNotRegisteredException(Exception):
    """User not registered"""


class PermissionAlreadyAllowedException(AlreadyDoneException):
    """Permission already allowed"""


class CantEditAdminPermissionOfNonAdminUserException(Exception):
    """Can't edit permission of non-admin user"""


class PermissionAlreadyRestrictedException(AlreadyDoneException):
    """Permission already restricted"""


class BannedUserNotFoundException(Exception):
    """Banned User with given id not found"""


class PlansBotUser:
    fields = ["id", "fullname", "state", "location", "section", "id_of_message_promoter_to_type", "is_admin",
              "is_owner", "receive_notifications", "able_to_switch_notifications", "current_catalog_menu"]
    full_admin_permissions = {permission_name: True for permission_name in permissions.keys()}
    default_admin_permissions = {permission_name: False for permission_name in permissions.keys()}
    collection_name = "Users"
    collection = mongo_db[collection_name]
    
    @property
    def editing_markup(self) -> types.InlineKeyboardMarkup:
        inline_kb = [[types.InlineKeyboardButton(text="Изменить ФИО", callback_data="EDIT USERS FULLNAME")],
                     [types.InlineKeyboardButton(text="Перенести в другой регион",
                                                 callback_data="EDIT USERS LOCATION")],
                     [types.InlineKeyboardButton(text="Перенести в другой отдел",
                                                 callback_data="EDIT USERS SECTION")],
                     [types.InlineKeyboardButton(
                         text=f"{'Отключить' if self.receive_notifications else 'Включить'} уведомления",
                         callback_data=f"SET USERS receive_notifications {'FALSE' if self.receive_notifications else 'TRUE'}")],
                     [types.InlineKeyboardButton(
                         text=f"{'Запретить' if self.able_to_switch_notifications else 'Разрешить'} управлять уведомлениями",
                         callback_data=f"SET USERS able_to_switch_notifications {'FALSE' if self.able_to_switch_notifications else 'TRUE'}")],
                     [types.InlineKeyboardButton(
                         text=f"{'Назначить администратором' if not self.is_admin else 'Разжаловать'}",
                         callback_data=f"SET USERS is_admin {'FALSE' if self.is_admin else 'TRUE'}")]]
        if self.is_admin:
            inline_kb.append([types.InlineKeyboardButton(text="Изменить права администратора",
                                                         callback_data="EDIT USERS ADMIN_PERMISSIONS")])
        inline_kb += [[types.InlineKeyboardButton(text="Удалить", callback_data="DELETE USER"),
                       types.InlineKeyboardButton(text="Заблокировать", callback_data="BAN USER")],
                      [types.InlineKeyboardButton(text="Завершить редактирование", callback_data="END EDITING USER")]]
        return types.InlineKeyboardMarkup(inline_keyboard=inline_kb)

    def get_field(self, field_name: str) -> Any:
        return self.collection.find_one({"id": self.id}, [field_name])[field_name]

    def get_admin_permissions_editing_text(self, chosen_permission_name: str) -> str:
        from classes import State
        text = f'Пользователь <code>{self.id}</code>:\n\nФИО: {self.fullname}\nРегион: {self.location}\nОтдел: {self.section}\nСтатус: {State.get_explanation(self.state)}\nОповещения: {"✅" if self.receive_notifications else "❌"}\nВозможность управлять оповещениями: {"✅" if self.able_to_switch_notifications else "❌"}\nАдмин: {"✅" if self.is_admin else "❌"}' + (
            f'\n\nПрава админа:' if self.is_admin else '')
        if self.is_admin:
            self_permissions = self.get_field('admin_permissions')
            for permission_name, permission_text in permissions.items():
                if chosen_permission_name == permission_name:
                    text += f'\n<u><b><i>{permission_text}</i></b></u> - {"✅" if self_permissions[permission_name] else "❌"}'
                else:
                    text += f'\n{permission_text} - {"✅" if self_permissions[permission_name] else "❌"}'
        return text

    def get_admin_permissions_editing_markup(self, chosen_permission_name: str) -> types.InlineKeyboardMarkup:
        previous_permission_name = list(permissions.keys())[list(permissions.keys()).index(chosen_permission_name)-1]
        next_permission_name = list(permissions.keys())[(list(permissions.keys()).index(chosen_permission_name)+1) % len(list(permissions.keys()))]
        return types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text='˄', callback_data=f'CHOOSE PERMISSION {previous_permission_name}')],
                                                           [types.InlineKeyboardButton(text=('Запретить' if self.is_allowed(chosen_permission_name) else 'Разрешить'),
                                                                                       callback_data=f'SET USERS A_P {chosen_permission_name} {"FALSE" if self.is_allowed(chosen_permission_name) else "TRUE"}')],
                                                           [types.InlineKeyboardButton(text='˅', callback_data=f'CHOOSE PERMISSION {next_permission_name}')],
                                                           [types.InlineKeyboardButton(text='<< Назад >>', callback_data='CANCEL EDITING ADMIN_PERMISSIONS')]])

    def __init__(self, tg_id: int,
                 fullname: str = "NONE",
                 state: str = 'NONE',
                 location: str = 'NONE',
                 section: str = 'NONE',
                 id_of_message_promoter_to_type: int = -1,
                 is_admin: bool = False,
                 is_owner: bool = False,
                 receive_notifications: bool = True,
                 able_to_switch_notifications: bool = False,
                 current_catalog_menu: str = 'main'):
        self._current_catalog_menu = current_catalog_menu
        self._able_to_switch_notifications = able_to_switch_notifications
        self._receive_notifications = receive_notifications
        self._is_owner = is_owner
        self._is_admin = is_admin
        self._id = tg_id
        self._fullname = fullname
        self._state = state
        self._location = location
        self._section = section
        self._id_of_message_promoter_to_type = id_of_message_promoter_to_type

    @property
    def id(self) -> int:
        return self._id

    @property
    def is_admin(self) -> bool:
        return self._is_admin

    @property
    def is_owner(self) -> bool:
        return self._is_owner

    @property
    def receive_notifications(self) -> bool:
        return self._receive_notifications

    @property
    def able_to_switch_notifications(self) -> bool:
        return self._able_to_switch_notifications

    @property
    def fullname(self) -> str:
        return self._fullname

    @property
    def state(self) -> str:
        return self._state

    @property
    def location(self) -> str:
        return self._location

    @property
    def section(self) -> str:
        return self._section

    @property
    def id_of_message_promoter_to_type(self) -> int:
        return self._id_of_message_promoter_to_type

    @property
    def current_catalog_menu(self) -> str:
        return self._current_catalog_menu

    def get_info(self, for_myself: bool = False) -> str:
        from classes import State
        text = f'Пользователь <code>{self.id}</code>{"(Вы)" if for_myself else""}:\n\nФИО: <code>{self.fullname}</code>\nРегион: <code>{self.location}</code>\nОтдел: <code>{self.section}</code>\nСтатус: <code>{State.get_explanation(self.state)}</code>\nОповещения: {"✅" if self.receive_notifications else "❌"}\nВозможность управлять оповещениями: {"✅" if self.able_to_switch_notifications else "❌"}\nАдмин: {"✅" if self.is_admin else "❌"}' + (
            f'\n\nПрава админа:' if self.is_admin else '')
        if self.is_admin:
            self_permissions = self.get_field('admin_permissions')
            for permission_name, permission_text in permissions.items():
                text += f'\n{permission_text} - {"✅" if self_permissions[permission_name] else "❌"}'
        return text

    @fullname.setter
    def fullname(self, fullname: str):
        self.__set_field("fullname", fullname)
        self._fullname = fullname

    @state.setter
    def state(self, state: str):
        self.__set_field("state", state)
        self._state = state
        if state == 'NONE':
            self.id_of_message_promoter_to_type = -1

    @location.setter
    def location(self, location: str):
        self.__set_field("location", location)
        self._location = location

    @section.setter
    def section(self, section: str):
        self.__set_field("section", section)
        self._section = section

    @id_of_message_promoter_to_type.setter
    def id_of_message_promoter_to_type(self, id_of_message_promoter_to_type: str):
        self.__set_field("id_of_message_promoter_to_type", id_of_message_promoter_to_type)
        self._id_of_message_promoter_to_type = id_of_message_promoter_to_type

    @is_admin.setter
    def is_admin(self, is_admin: bool):
        if self._is_admin is is_admin:
            raise AdminAlreadyPromotedException(
                f'User: "{self.fullname}" {self.id}') if is_admin else AdminAlreadyDismissedException(
                f'User: "{self.fullname}" {self.id}')
        self.__set_field("is_admin", is_admin)
        self.collection.update_one({"id": self._id},
                                   {"$set": {"admin_permissions": self.__class__.default_admin_permissions}})
        self._is_admin = is_admin

    @receive_notifications.setter
    def receive_notifications(self, receive_notifications: bool):
        self._receive_notifications = receive_notifications
        self.__set_field("receive_notifications", receive_notifications)

    @able_to_switch_notifications.setter
    def able_to_switch_notifications(self, able_to_switch_notifications: bool):
        self.__set_field("able_to_switch_notifications", able_to_switch_notifications)
        self._able_to_switch_notifications = able_to_switch_notifications

    @current_catalog_menu.setter
    def current_catalog_menu(self, current_catalog_menu: bool):
        self.__set_field('current_catalog_menu', current_catalog_menu)
        self._current_catalog_menu = current_catalog_menu

    def is_allowed(self, permission_name: str) -> bool:
        return bool(self.collection.find_one({"id": self.id})["admin_permissions"].get(permission_name, False))

    def allow_permission(self, user_id: int, permission_name: str):
        if not self.is_owner:
            if not self.is_admin:
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is not admin.')
            if not self.is_allowed('choose_admins'):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is admin but have not this permission')
            if not self.is_higher(user_id):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is admin and have this permission but he is lower than user {user_id}')
            if permission_name == 'choose_admins':
                raise PermissionDeniedException(f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is admin and have this permission but he is not owner and can not allow someone to choose admins.')
        user = PlansBotUser.get_by_id(user_id)
        if not user.is_admin:
            raise CantEditAdminPermissionOfNonAdminUserException(f'User: "{user.fullname}" {user.id}')
        if user.is_allowed(permission_name):
            raise PermissionAlreadyAllowedException(f'User: {user_id}. Permission: {permission_name}.')
        if permission_name == 'choose_admins':
            self.__set_field_by_id(user_id, "admin_permissions", self.__class__.full_admin_permissions)
        else:
            self.__set_field_by_id(user_id, f"admin_permissions.{permission_name}", True)

    def restrict_permission(self, user_id: int, permission_name: str):
        if not self.is_owner:
            if not self.is_admin:
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is not admin.')
            if not self.is_allowed('choose_admins'):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is admin but have not this permission')
            if not self.is_higher(user_id):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: /ban. Reason: user is admin and have this permission but he is lower than user {user_id}')
            if permission_name == 'choose_admins':
                raise PermissionDeniedException(f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is admin and have this permission but he is not owner and can not allow someone to choose admins.')
        user = PlansBotUser.get_by_id(user_id)
        if not user.is_admin:
            raise CantEditAdminPermissionOfNonAdminUserException(f'User: "{user.fullname}" {user.id}')
        if not user.is_allowed(permission_name):
            raise PermissionAlreadyRestrictedException(f'User: {user_id}. Permission: {permission_name}.')
        if permission_name != 'choose_admins':
            self.__class__.__set_field_by_id(user_id, "admin_permissions.choose_admins", False)
        self.__class__.__set_field_by_id(user_id, f"admin_permissions.{permission_name}", False)

    def is_higher(self, user_id: int) -> bool:
        user = PlansBotUser.get_by_id(user_id)
        return self.is_owner or (
               self.is_allowed('choose_admins') and not user.is_allowed('choose_admins')) or (
               self.is_admin and not user.is_admin)

    def ban(self, user_id: int):
        if not self.is_owner:
            if not self.is_admin:
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: /ban. Reason: user is not admin.')
            if not self.is_allowed('/ban'):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: /ban. Reason: user is admin but have not this permission')
            if not self.is_higher(user_id):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: /ban. Reason: user is admin and have this permission but he is lower than user {user_id}')
        self.__class__.ban_by_id(user_id)

    def kick(self, user_id: int):
        if not self.is_owner:
            if not self.is_admin:
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: /kick. Reason: user is not admin.')
            if not self.is_allowed('/kick'):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: /kick. Reason: user have not this permission')
            if not self.is_higher(user_id):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: /kick. Reason: user is admin and have this permission but he is lower than user {user_id}')
        self.__class__.delete_by_id(user_id)

    @staticmethod
    def exists_by_id(user_id: int) -> bool:
        return mongo_db['Users'].find_one({'id': user_id}) is not None

    @classmethod
    def registered_by_id(cls, user_id: int) -> bool:
        if not cls.exists_by_id(user_id):
            return False
        return cls.get_by_id(user_id).state not in ['CHOOSING LOCATION', 'CHOOSING SECTION', 'TYPING FULLNAME',
                                                    'WAITING FOR REG CONFIRMATION']

    def registered(self) -> bool:
        return self.state not in ['CHOOSING LOCATION', 'CHOOSING SECTION', 'TYPING FULLNAME',
                                  'WAITING FOR REG CONFIRMATION']

    def promote_to_admin(self, user_id: int):
        if not self.__class__.registered_by_id(user_id):
            raise UserNotRegisteredException(f'User: "{user_id}.')
        if not self.is_owner:
            if not self.is_admin:
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is not admin.')
            if not self.is_allowed('choose_admins'):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is admin but have not this permission')
            if not self.is_higher(user_id):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is admin and have this permission but he is lower than user {user_id}')
        user = self.__class__.get_by_id(user_id)
        user.is_admin = True

    def dismiss_admin(self, user_id: int):
        if not self.__class__.registered_by_id(user_id):
            raise UserNotRegisteredException(f'User: "{user_id}.')
        if not self.is_owner:
            if not self.is_admin:
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is not admin.')
            if not self.is_allowed('choose_admins'):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is admin but have not this permission')
            if not self.is_higher(user_id):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: choose_admins. Reason: user is admin and have this permission but he is lower than user {user_id}')
        user = self.__class__.get_by_id(user_id)
        user.is_admin = False

    @classmethod
    def reg(cls, tg_id: int) -> PlansBotUser:
        if not cls.exists_by_id(tg_id):
            new_user = PlansBotUser(tg_id)
            cls.collection.insert_one(new_user.to_json())
        return cls.get_by_id(tg_id)

    @classmethod
    def get_by_id(cls, tg_id: int) -> PlansBotUser:
        user_dict = cls.collection.find_one({"id": tg_id}, cls.fields)
        if user_dict is None:
            raise UserNotFoundException(f'ID: {tg_id}')
        return cls.from_json(user_dict)

    async def send_message(self, text: str, reply_to_message_id: int | None = None,
                           markup: types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None = None):
        try:
            return await bot.send_message(self.id, text, reply_to_message_id=reply_to_message_id, reply_markup=markup,
                                          parse_mode='HTML')
        except:
            ...

    async def send_message_with_no_try(self, text: str, reply_to_message_id: int | None = None,
                           markup: types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None = None) -> types.Message:
            return await bot.send_message(self.id, text, reply_to_message_id=reply_to_message_id, reply_markup=markup,
                                          parse_mode='HTML')

    async def edit_state_message(self, text: str,
                                 markup: types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None = None) -> types.Message:
        return await bot.edit_message_text(text, chat_id=self.id, message_id=self.id_of_message_promoter_to_type, reply_markup=markup,
                                           parse_mode='HTML')

    async def delete_state_message(self):
        try:
            await bot.delete_message(self.id, self.id_of_message_promoter_to_type)
        except:
            try:
                await bot.edit_message_reply_markup(self.id, self.id_of_message_promoter_to_type, reply_markup=None)
            except:
                ...

    @classmethod
    def get_users_that_not_sent_plans(cls, checking_date: date) -> List[PlansBotUser] | list:
        from classes import Plan
        user_dicts = cls.collection.find({})
        users = []
        for user in user_dicts:
            if Plan.get_by_date_and_user_id(user["id"],
                                            f'{checking_date.day}.{checking_date.month}.{checking_date.year}') is None:
                users.append(cls.from_json(user))
        return users

    @classmethod
    def get_users_that_sent_plans(cls, checking_date: date) -> List[PlansBotUser] | list:
        from classes import Plan
        user_dicts = cls.collection.find({})
        users = []
        for user in user_dicts:
            if Plan.get_by_date_and_user_id(user["id"],
                                            f'{checking_date.day}.{checking_date.month}.{checking_date.year}') is not None:
                users.append(cls.from_json(user))
        return users

    @classmethod
    def get_all(cls) -> List[PlansBotUser] | list:
        user_dicts = cls.collection.find({})
        users = []
        for user in user_dicts:
            users.append(cls.from_json(user))
        return users

    @classmethod
    def delete_by_id(cls, tg_id: int):
        if not cls.exists_by_id(tg_id):
            raise UserNotFoundException(f'ID: {tg_id}')
        from classes import Plan
        cls.collection.delete_one({"id": tg_id})
        Plan.delete_all_by_user_id(tg_id)

    @classmethod
    def ban_by_id(cls, tg_id: int):
        fullname = 'Не известно'
        if cls.is_banned_by_id(tg_id):
            raise AlreadyDoneException(f'User: {tg_id} already banned!')
        try:
            ban_user = cls.get_by_id(tg_id)
            if ban_user.fullname != 'NONE':
                fullname = ban_user.fullname
        except UserNotFoundException as exception:
            raise exception
        finally:
            mongo_db["BannedUsers"].insert_one({"id": tg_id, "fullname": fullname})
            cls.delete_by_id(tg_id)

    @classmethod
    def is_banned_by_id(cls, tg_id: int):
        if mongo_db["BannedUsers"].find_one({"id": tg_id}):
            return True
        return False

    @classmethod
    def unban_by_id(cls, tg_id: int):
        mongo_db["BannedUsers"].delete_one({"id": tg_id})

    @classmethod
    def migrate(cls, new_field: str, default_value):
        for user_dict in cls.collection.find({}):
            if new_field not in user_dict.keys():
                cls.collection.update_one({"id": user_dict["id"]}, {"$set": {new_field: default_value}})

    @classmethod
    def migrate_add_new_permission(cls, new_perm: str):
        for user_dict in cls.collection.find({}):
            if "admin_permissions" in user_dict.keys() and new_perm not in user_dict["admin_permissions"].keys():
                cls.collection.update_one({"id": user_dict["id"]}, {"$set": {f"admin_permissions.{new_perm}": user_dict["admin_permissions"]["choose_admins"]}})

    @property
    def is_editing_by_someone(self) -> IsEditingResult:
        user_json = mongo_db['Users'].find_one({"state": {"$regex": f"{self.id}$"}}, ["id"])
        if user_json:
            return IsEditingResult(True, PlansBotUser.get_by_id(user_json["id"]))
        return IsEditingResult(False, None)

    def set_field(self, user_to_edit_id: int, field: str, value: Any):
        if not self.is_owner:
            permission_name = f'edit_users_{field if field not in ["receive_notifications", "able_to_switch_notifications"] else "notifications"}'
            if not self.is_admin:
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: {permission_name}. Reason: user is not admin.')

            if not self.is_higher(user_to_edit_id):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: {permission_name}. Reason: user is admin and have this permission but he is lower than user {user_to_edit_id}')
        self.__class__.__set_field_by_id(user_to_edit_id, field, value)

    def unban(self, user_id: int):
        if not self.is_owner:
            if not self.is_admin:
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: /unban. Reason: user is not admin.')
            if not self.is_allowed('/unban'):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: /unban. Reason: user is admin but have not this permission')
        self.__class__.unban_by_id(user_id)

    @staticmethod
    def get_banned_user_fullname_by_id(user_id: int) -> str:
        banned_user_dict = mongo_db["BannedUsers"].find_one({"id": user_id})
        if not banned_user_dict:
            raise BannedUserNotFoundException()
        return banned_user_dict["fullname"]

    @property
    def help_message_text(self) -> str:
        text = 'Вот список команд доступных для вас:'
        from bot.commands import commands
        self_permissions = self.get_field("admin_permissions")
        for command_name, command_info in commands.items():
            ok = True
            for permission_name in command_info.required_permissions:
                if not self_permissions[permission_name]:
                    ok = False
                    break
            if ok:
                text += f'\n{command_name} - {command_info.explanation}'
        return text

    @classmethod
    def get_responders(cls) -> List[PlansBotUser] | list:
        return list(map(cls.from_json, cls.collection.find({"admin_permissions.responder": True})))

    def to_json(self) -> dict:
        return {field: self.__getattribute__(field) for field in self.__class__.fields}

    @classmethod
    def from_json(cls, data: dict) -> PlansBotUser:
        return cls(*[data[field] for field in cls.fields])

    def __set_field(self, field: str, value: Any):
        self.__class__.__set_field_by_id(self._id, field, value)

    @classmethod
    def __set_field_by_id(cls, _id: int, field: str, value: Any):
        cls.collection.update_one({"id": _id}, {"$set": {field: value}})

    async def send_photo(self, document: types.FSInputFile | types.URLInputFile, caption:  str, reply_to_message_id: int | None = None, reply_markup: types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None = None):
        await bot.send_photo(self.id, document, caption=caption, parse_mode="HTML", reply_markup=reply_markup,
                             reply_to_message_id=reply_to_message_id)

    async def send_video(self, document: types.FSInputFile | types.URLInputFile, caption:  str, reply_to_message_id: int | None = None, reply_markup: types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None = None):
        await bot.send_video(self.id, document, caption=caption, parse_mode="HTML", reply_markup=reply_markup,
                             reply_to_message_id=reply_to_message_id)

    async def send_audio(self, document: types.FSInputFile | types.URLInputFile, caption:  str, reply_to_message_id: int | None = None, reply_markup: types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None = None):
        await bot.send_audio(self.id, document, caption=caption, parse_mode="HTML", reply_markup=reply_markup,
                             reply_to_message_id=reply_to_message_id)

    async def send_document(self, document: types.FSInputFile | types.URLInputFile, caption:  str, reply_to_message_id: int | None = None, reply_markup: types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None = None):
        await bot.send_document(self.id, document, caption=caption, parse_mode="HTML", reply_markup=reply_markup,
                                reply_to_message_id=reply_to_message_id)

    async def send_media_group(self, media_list: List[types.InputMediaAudio | types.InputMediaDocument | types.InputMediaPhoto | types.InputMediaVideo], reply_to_message_id: int | None = None):
        await bot.send_media_group(self.id, media_list,
                                   reply_to_message_id=reply_to_message_id)

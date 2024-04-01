from __future__ import annotations
from datetime import date
from admin_permission import permissions
from create_bot import bot
from mongo_connector import mongo_db
from aiogram import types
from typing import NamedTuple, Any


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
    full_admin_permissions = {perm_name: True for perm_name in permissions.keys()}
    default_admin_permissions = {perm_name: False for perm_name in permissions.keys()}

    @property
    def editing_markup(self):
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

    def get_field(self, field_name: str):
        return mongo_db["Users"].find_one({"id": self.id}, [field_name])[field_name]

    def get_admin_permissions_editing_text(self, chosen_permission_name: str):
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

    def get_admin_permissions_editing_markup(self, chosen_permission_name: str):
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
        self.__current_catalog_menu = current_catalog_menu
        self.__able_to_switch_notifications = able_to_switch_notifications
        self.__receive_notifications = receive_notifications
        self.__is_owner = is_owner
        self.__is_admin = is_admin
        self.__id = tg_id
        self.__fullname = fullname
        self.__state = state
        self.__location = location
        self.__section = section
        self.__id_of_message_promoter_to_type = id_of_message_promoter_to_type

    @property
    def id(self):
        return self.__id

    @property
    def is_admin(self):
        return self.__is_admin

    @property
    def is_owner(self):
        return self.__is_owner

    @property
    def receive_notifications(self):
        return self.__receive_notifications

    @property
    def able_to_switch_notifications(self):
        return self.__able_to_switch_notifications

    @property
    def fullname(self):
        return self.__fullname

    @property
    def state(self):
        return self.__state

    @property
    def location(self):
        return self.__location

    @property
    def section(self):
        return self.__section

    @property
    def id_of_message_promoter_to_type(self):
        return self.__id_of_message_promoter_to_type

    @property
    def current_catalog_menu(self):
        return self.__current_catalog_menu

    def get_info(self, for_myself: bool = False):
        from classes import State
        text = f'Пользователь <code>{self.id}</code>{"(Вы)" if for_myself else""}:\n\nФИО: {self.fullname}\nРегион: {self.location}\nОтдел: {self.section}\nСтатус: {State.get_explanation(self.state)}\nОповещения: {"✅" if self.receive_notifications else "❌"}\nВозможность управлять оповещениями: {"✅" if self.able_to_switch_notifications else "❌"}\nАдмин: {"✅" if self.is_admin else "❌"}' + (
            f'\n\nПрава админа:' if self.is_admin else '')
        if self.is_admin:
            self_permissions = self.get_field('admin_permissions')
            for permission_name, permission_text in permissions.items():
                text += f'\n{permission_text} - {"✅" if self_permissions[permission_name] else "❌"}'
        return text

    @fullname.setter
    def fullname(self, fullname: str):
        self.__fullname = fullname
        mongo_db["Users"].update_one({"id": self.id}, {"$set": {"fullname": fullname}})

    @state.setter
    def state(self, state: str):
        self.__state = state
        mongo_db["Users"].update_one({"id": self.id}, {"$set": {"state": state}})
        if state == 'NONE':
            self.id_of_message_promoter_to_type = -1

    @location.setter
    def location(self, location: str):
        self.__location = location
        mongo_db["Users"].update_one({"id": self.id}, {"$set": {"location": location}})

    @section.setter
    def section(self, section: str):
        self.__section = section
        mongo_db["Users"].update_one({"id": self.id}, {"$set": {"section": section}})

    @id_of_message_promoter_to_type.setter
    def id_of_message_promoter_to_type(self, id_of_message_promoter_to_type: str):
        self.__id_of_message_promoter_to_type = id_of_message_promoter_to_type
        mongo_db["Users"].update_one({"id": self.id},
                                     {"$set": {"id_of_message_promoter_to_type": id_of_message_promoter_to_type}})

    @is_admin.setter
    def is_admin(self, is_admin: bool):
        self.__is_admin = is_admin
        if self.__is_admin is is_admin:
            raise AdminAlreadyPromotedException(
                f'User: "{self.fullname}" {self.id}') if is_admin else AdminAlreadyDismissedException(
                f'User: "{self.fullname}" {self.id}')
        mongo_db["Users"].update_one({"id": self.id}, {"$set": {"is_admin": is_admin}})

    @receive_notifications.setter
    def receive_notifications(self, receive_notifications: bool):
        self.__receive_notifications = receive_notifications
        mongo_db["Users"].update_one({"id": self.id}, {"$set": {"receive_notifications": receive_notifications}})

    @able_to_switch_notifications.setter
    def able_to_switch_notifications(self, able_to_switch_notifications: bool):
        self.__able_to_switch_notifications = able_to_switch_notifications
        mongo_db["Users"].update_one({"id": self.id},
                                     {"$set": {"able_to_switch_notifications": able_to_switch_notifications}})

    @current_catalog_menu.setter
    def current_catalog_menu(self, current_catalog_menu: bool):
        self.__current_catalog_menu = current_catalog_menu
        mongo_db["Users"].update_one({"id": self.id},
                                     {"$set": {"current_catalog_menu": current_catalog_menu}})

    def is_allowed(self, permission_name: str):
        return bool(mongo_db["Users"].find_one({"id": self.id})["admin_permissions"].get(permission_name, False))

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
            mongo_db["Users"].update_one({"id": user_id}, {"$set": {"admin_permissions": self.__class__.full_admin_permissions}})
        else:
            mongo_db["Users"].update_one({"id": user_id}, {"$set": {f"admin_permissions.{permission_name}": True}})

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
            mongo_db["Users"].update_one({"id": user_id}, {"$set": {f"admin_permissions.choose_admins": False}})
        mongo_db["Users"].update_one({"id": user_id}, {"$set": {f"admin_permissions.{permission_name}": False}})

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
    def exists_by_id(user_id: int):
        return mongo_db['Users'].find_one({'id': user_id}) is not None

    @classmethod
    def registered_by_id(cls, user_id: int):
        if not cls.exists_by_id(user_id):
            return False
        return cls.get_by_id(user_id).state not in ['CHOOSING LOCATION', 'CHOOSING SECTION', 'TYPING FULLNAME',
                                                    'WAITING FOR REG CONFIRMATION']

    def registered(self):
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
        user = mongo_db['Users'].find_one({'id': user_id})
        if user["is_admin"]:
            raise AdminAlreadyPromotedException(f'Admin: "{user["fullname"]}" {user_id}')
        mongo_db["Users"].update_one({"id": user_id},
                                     {"$set": {"admin_permissions": self.__class__.default_admin_permissions}})
        mongo_db["Users"].update_one({"id": user_id},
                                     {"$set": {"is_admin": True}})

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
        user = mongo_db['Users'].find_one({'id': user_id})
        if not self.is_owner and user["admin_permissions"]["choose_admins"]:
            raise PermissionDeniedException(
                f'Admin: "{user["fullname"]}" {user["id"]}. Can not dismiss admin with choose_admins_permissions if dismisser is not owner.')
        if not user["is_admin"]:
            raise AdminAlreadyDismissedException(f'Admin: "{user["fullname"]}" {user_id}')
        mongo_db["Users"].update_one({"id": user_id},
                                     {"$set": {"admin_permissions": self.__class__.default_admin_permissions}})
        mongo_db["Users"].update_one({"id": user_id},
                                     {"$set": {"is_admin": False}})

    @classmethod
    def reg(cls, tg_id: int):
        """
        :rtype :PlansBotUser
        """
        if not cls.exists_by_id(tg_id):
            new_user = PlansBotUser(tg_id)
            mongo_db["Users"].insert_one({"id": new_user.id,
                                          "fullname": new_user.fullname,
                                          "state": new_user.state,
                                          "location": new_user.location,
                                          "section": new_user.section,
                                          "id_of_message_promoter_to_type": new_user.id_of_message_promoter_to_type,
                                          "is_owner": new_user.is_owner,
                                          "is_admin": new_user.is_admin,
                                          "receive_notifications": new_user.receive_notifications,
                                          "able_to_switch_notifications": new_user.able_to_switch_notifications,
                                          "current_catalog_menu": new_user.current_catalog_menu,
                                          "admin_permissions": PlansBotUser.default_admin_permissions
                                          })
        return cls.get_by_id(tg_id)

    @classmethod
    def from_json(cls, user_dict):
        return cls(user_dict["id"],
                   user_dict["fullname"],
                   user_dict["state"],
                   user_dict["location"],
                   user_dict["section"],
                   user_dict["id_of_message_promoter_to_type"],
                   user_dict["is_admin"],
                   user_dict["is_owner"],
                   user_dict["receive_notifications"],
                   user_dict["able_to_switch_notifications"],
                   user_dict["current_catalog_menu"]
                   )

    @classmethod
    def get_by_id(cls, tg_id: int):
        """
        :rtype :PlansBotUser
        """
        user_dict = mongo_db["Users"].find_one({"id": tg_id}, cls.fields)
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

    async def edit_state_message(self, text: str,
                                 markup: types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None = None):
        return await bot.edit_message_text(text, self.id, self.id_of_message_promoter_to_type, reply_markup=markup,
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
    def get_users_that_not_sent_plans(cls, checking_date: date):
        from classes import Plan
        user_dicts = mongo_db["Users"].find({})
        users = []
        for user in user_dicts:
            if Plan.get_by_date_and_user_id(user["id"],
                                            f'{checking_date.day}.{checking_date.month}.{checking_date.year}') is None:
                users.append(cls.from_json(user))
        return users

    @classmethod
    def get_users_that_sent_plans(cls, checking_date: date):
        from classes import Plan
        user_dicts = mongo_db["Users"].find({})
        users = []
        for user in user_dicts:
            if Plan.get_by_date_and_user_id(user["id"],
                                            f'{checking_date.day}.{checking_date.month}.{checking_date.year}') is not None:
                users.append(cls.from_json(user))
        return users

    @classmethod
    def get_all(cls):
        user_dicts = mongo_db["Users"].find({})
        users = []
        for user in user_dicts:
            users.append(cls.from_json(user))
        return users

    @classmethod
    def delete_by_id(cls, tg_id: int):
        if not cls.exists_by_id(tg_id):
            raise UserNotFoundException(f'ID: {tg_id}')
        from classes import Plan
        mongo_db["Users"].delete_one({"id": tg_id})
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
        for user_dict in mongo_db["Users"].find({}):
            if new_field not in user_dict.keys():
                mongo_db["Users"].update_one({"id": user_dict["id"]}, {"$set": {new_field: default_value}})

    @property
    def is_editing_by_someone(self):
        user_json = mongo_db['Users'].find_one({"state": {"$regex": f"{self.id}$"}}, ["id"])
        if user_json:
            return True, PlansBotUser.get_by_id(user_json["id"])
        return IsEditingResult(False, None)

    def set_field(self, user_to_edit_id: int, field_name: str, value: Any):
        if not self.is_owner:
            permission_name = f'edit_users_{field_name if field_name not in ["receive_notifications", "able_to_switch_notifications"] else "notifications"}'
            if not self.is_admin:
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: {permission_name}. Reason: user is not admin.')

            if not self.is_higher(user_to_edit_id):
                raise PermissionDeniedException(
                    f'User: "{self.fullname}" {self.id}. Permission: {permission_name}. Reason: user is admin and have this permission but he is lower than user {user_to_edit_id}')
        mongo_db["Users"].update_one({"id": user_to_edit_id}, {"$set": {field_name: value}})

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
    def get_banned_user_fullname_by_id(user_id: int):
        banned_user_dict = mongo_db["BannedUsers"].find_one({"id": user_id})
        if not banned_user_dict:
            raise BannedUserNotFoundException()
        return banned_user_dict["fullname"]

    @property
    def help_message_text(self):
        text = 'Вот список команд доступных для вас:'
        from commands import commands
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


from aiogram.dispatcher.flags import get_flag

from check_message_types import is_command
from classes import PlansBotUser
from create_bot import dp
from aiogram import types

from filters import StateFilter


async def get_user_update_outer_middleware(handler: callable,
                                           event: types.Update,
                                           data: dict):
    data["is_user_banned"] = PlansBotUser.is_banned_by_id(event.event.from_user.id)
    data['user_exists'] = PlansBotUser.exists_by_id(event.event.from_user.id)
    data['user'] = PlansBotUser.get_by_id(event.event.from_user.id) if data['user_exists'] else None
    await handler(event, data)


async def permission_checker_callback_query_middleware(handler: callable, event: types.Update, data: dict):
    if not data["user_exists"] or data["user"].is_owner:
        return await handler(event, data)
    permissions = get_flag(data, 'required_permissions', default=[])
    for permission in permissions:
        if data["user"].is_owner:
            return await handler(event, data)
        if not data["user"].is_allowed(permission):
            return await event.answer("У вас недостаточно прав для использования этой функции", True)
    return await handler(event, data)


async def permission_checker_message_middleware(handler: callable, event: types.Message, data: dict):
    if not data["user_exists"] or data["user"].is_owner:
        return await handler(event, data)
    permissions = get_flag(data, 'required_permissions', default=[])
    for permission in permissions:
        if not data["user"].is_allowed(permission):
            if is_command(event):
                return await event.reply(
                    "У вас недостаточно прав для использования этой команды!")
            return await event.reply(
                "У вас недостаточно прав для завершения этого действия!")
    return await handler(event, data)


async def state_message_checker_callback_query_middleware(handler: callable, event: types.Update, data: dict):
    check_state_message = get_flag(data, 'check_state_message', default=False)
    if check_state_message and event.message.message_id != data["user"].id_of_message_promoter_to_type:
        return await event.answer('Сообщение устарело!', True)
    return await handler(event, data)


async def state_checker_callback_query_middleware(handler: callable, event: types.Update, data: dict):
    state_filter: StateFilter = get_flag(data, 'state_filter', default=None)
    if state_filter is not None and not state_filter(user=data["user"]):
        return await event.answer(get_flag(data, 'state_error_message'), True)
    return await handler(event, data)


def register_middleware():
    dp.update.outer_middleware.register(get_user_update_outer_middleware)
    dp.message.middleware.register(permission_checker_message_middleware)
    dp.callback_query.middleware.register(state_checker_callback_query_middleware)
    dp.callback_query.middleware.register(state_message_checker_callback_query_middleware)
    dp.callback_query.middleware.register(permission_checker_callback_query_middleware)

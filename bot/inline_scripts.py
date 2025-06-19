import uuid

from aiogram import types

from classes import PlansBotUser
from create_bot import router


async def handler(query: types.InlineQuery, user: PlansBotUser):
    if not user.is_owner and not user.is_allowed('invite_new_users'):
        await query.answer([], 1, switch_pm_text="У вас недостаточно полномочий")
    results = []
    results.append(types.InlineQueryResultArticle(id=uuid.uuid4().hex,
                                                  title='Отправить приглашение',
                                                  input_message_content=types.InputTextMessageContent(message_text='Приглашаю Вас присоединиться к боту, менеджеру планов компании OVM Group'),
                                                  reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(
                                                      text='Присоединиться',
                                                      callback_data='JOIN')]])))
    await query.answer(results, 1)


async def no_access(query: types.InlineQuery):
    await query.answer([], 1, switch_pm_text="У вас нет доступа к боту", switch_pm_parameter="_")


def reg_handlers():
    router.inline_query.register(no_access, lambda _, user_exists: not user_exists)
    router.inline_query.register(handler)

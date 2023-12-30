from aiogram import types

from create_bot import router


async def holidays_handler(msg: types.Message):
    await msg.delete()
    await msg.answer('Значится вы не работаете, а я должен? Нет, так не пойдёт!\n\nПриходите после праздников)')


def reg_handlers():
    router.message.register(holidays_handler)

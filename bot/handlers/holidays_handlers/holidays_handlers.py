from aiogram import types
from aiogram.filters import Command

from classes import PlansBotUser
from config import switch_holidays_key
from create_bot import router


async def holidays_handler(msg: types.Message):
    await msg.delete()
    await msg.answer('С новым годом, дорогой сотрудник) 🎉')
    await msg.answer('А пока вы отдыхаете, я тоже возьму себе отпуск, возвращайтесь после праздников')


async def switch_holidays_command(message: types.Message):
    switch_holidays_key()
    await message.answer('Режим праздников выключён, бот перезапускается...')
    import os
    os.system("bash main.sh")


def reg_handlers():
    router.message.register(switch_holidays_key, Command("switch_holidays"), lambda msg: PlansBotUser.get_by_id(msg.from_user.id).is_allowed("/restart"))
    router.message.register(holidays_handler)

from config import TOKEN
from aiogram import Bot, Dispatcher, Router

bot = Bot(TOKEN)
bot.parse_mode = 'HTML'
dp = Dispatcher()
router = Router()
dp.include_router(router)

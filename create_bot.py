from config import TOKEN
from aiogram import Bot, Dispatcher, Router

bot = Bot(TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

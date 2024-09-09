import asyncio
import logging
from datetime import datetime
from random import randint
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from classes import InlineButton, SendMessageAction, Session
from config import BY_WEBHOOK, BASE_WEBHOOK_URL
from create_bot import dp, bot
from register import register_handlers

WEB_SERVER_HOST = "127.0.0.1"
WEB_SERVER_PORT = 5000
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = str(randint(1, 1000000))

async def on_startup_webhook() -> None:
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}", secret_token=WEBHOOK_SECRET)


def start_bot_webhook() -> None:
    dp.startup.register(on_startup_webhook)
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


async def start_bot_polling():
    await bot.delete_webhook()
    await dp.start_polling(bot)


def main():
    if BY_WEBHOOK:
        start_bot_webhook()
    else:
        asyncio.run(start_bot_polling())


if __name__ == "__main__":
    logging.basicConfig(filename='LOG.log')
    logging.log(level=logging.INFO, msg=f'STARTED GMT +0 "{datetime.now()}"')
    register_handlers()
    main()
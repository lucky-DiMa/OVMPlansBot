from aiogram.exceptions import TelegramNetworkError
from create_bot import router


def restart(error):
    import os
    os.system("bash main.sh")


def reg_handlers():
    router.errors.register(restart, lambda error: isinstance(error, TelegramNetworkError))
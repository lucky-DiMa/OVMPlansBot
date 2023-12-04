from aiogram.types import Message


def is_command(message: Message):
    if not message.entities:
        return False
    for entity in message.entities:
        if entity.type == 'bot_command':
            return True
    return False

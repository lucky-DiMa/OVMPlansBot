import callback_scripts
import holidays_handlers
import inline_scripts
import middleware
import telegram_disconnection_errors
import text_scripts
from config import HOLIDAYS


def register_handlers():
    if not HOLIDAYS:
        middleware.register_middleware()
        callback_scripts.reg_handlers()
        inline_scripts.reg_handlers()
        text_scripts.reg_handlers()
        telegram_disconnection_errors.reg_handlers()
    else:
        holidays_handlers.reg_handlers()

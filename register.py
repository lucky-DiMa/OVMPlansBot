import callback_scripts, text_scripts, middleware, inline_scripts, telegram_disconnection_errors


def register_handlers():
    middleware.register_middleware()
    callback_scripts.reg_handlers()
    inline_scripts.reg_handlers()
    text_scripts.reg_handlers()
    telegram_disconnection_errors.reg_handlers()

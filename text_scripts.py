import re
from datetime import date, timedelta, datetime
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import KeyboardBuilder, ReplyKeyboardBuilder

from classes.plans_bot_user import UserNotFoundException, PermissionDeniedException
from config import switch_holidays_key
from cron import send_notifications
from aiogram import types, F

from check_message_types import is_command
from classes import PlansBotUser, Plan, Email, State, CatalogItem, AccessRequest
from create_bot import router, bot
from filters import StateFilter
from mongo_connector import mongo_db
from mytime import next_send_day, beauty_date


async def first_start_command(message: types.Message):
    await message.delete()
    await message.answer('Дорогой сотрудник, добро пожаловать в бота OVM group!')
    await message.answer(
        'Пожалуйста отправьте мне своё ФИО! Чтобы отменить регистрацию используйте команду /cancel')
    user = PlansBotUser.reg(message.from_user.id)
    user.state = 'TYPING FULLNAME'


async def catalog_command(message: types.Message, user: PlansBotUser):
    user.current_catalog_menu = 'main'
    items = CatalogItem.get_by_prev_catalog_item_text('main')
    kb_builder = ReplyKeyboardBuilder()
    for item in items:
        kb_builder.button(text=item.text)
    kb_builder.adjust(2, repeat=True)
    await message.delete()
    await message.answer('Catalog:', reply_markup=kb_builder.as_markup(resize_keyboard=True))



async def start_command(message: types.Message, user: PlansBotUser):
    await message.delete()
    await message.answer(f'Приветствую вас <code>{user.fullname}</code>!', parse_mode='HTML')


async def all_messages(message: types.Message, user: PlansBotUser):
    item = CatalogItem.get_by_text(message.text)
    if message.text == 'Назад' and user.current_catalog_menu != 'main':
        previous_catalog_item_text = CatalogItem.get_by_text(user.current_catalog_menu).prev_catalog_item_text
        if previous_catalog_item_text == 'main':
            user.current_catalog_menu = 'main'
            items = CatalogItem.get_by_prev_catalog_item_text('main')
            kb_builder = ReplyKeyboardBuilder()
            for item in items:
                kb_builder.button(text=item.text)
            kb_builder.adjust(2, repeat=True)
            await message.answer('Catalog:', reply_markup=kb_builder.as_markup(resize_keyboard=True))
            return
        else:
            item = CatalogItem.get_by_text(CatalogItem.get_by_text(user.current_catalog_menu).prev_catalog_item_text)
    if not item:
        await message.reply('Что вы говорите??\n/help - список команд')
    else:
        await item.process_tap(user)


async def no(_):
    pass


async def place_message(message: types.Message, user: PlansBotUser):
    if is_command(message):
        await message.reply('Извините нельзя использовать команды! :)')
        return
    await message.delete()
    str_date = user.state.split()[-1]
    user.state = 'NONE'
    if Plan.get_by_date_and_user_id(message.from_user.id, str_date) is None:
        Plan.create(user.id, f'На выезде {message.text}', str_date)
        await user.send_message('Спасибо за оставленный план!')
    else:
        plan = Plan.get_by_date_and_user_id(message.from_user.id,
                                            str_date)
        plan.text = f'На выезде {message.text}'
        await user.send_message('План успешно отредактирован!')
    await user.delete_state_message()


async def send_plan_command(message: types.Message, user: PlansBotUser):
    await message.delete()
    str_date = f'{next_send_day().day}.{next_send_day().month}.{next_send_day().year}'
    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[
        [types.InlineKeyboardButton(text='В ОФИСЕ', callback_data=f'SEND IN OFFICE PLAN {str_date}'),
         types.InlineKeyboardButton(text='НА ВЫЕЗДЕ', callback_data=f'SEND PLACE WHERE YOU WILL BE {str_date}')],
        [types.InlineKeyboardButton(text='В  ОТПУСКЕ', callback_data=f'SEND START WORK DATE AFTER VACATION {str_date}'),
         types.InlineKeyboardButton(text='НА БОЛЬНИЧНОМ', callback_data=f'SEND START WORK DATE AFTER SICK {str_date}')]])
    if Plan.get_by_date_and_user_id(user.id,
                                    str_date) is not None:
        await user.send_message(
            f'Вы редактируете уже написанный план на {beauty_date(str_date)} <code>{Plan.get_by_date_and_user_id(user.id, str_date).text}</code>',
            markup=markup)
        return
    await user.send_message(f'Выберете где вы будете в {beauty_date(str_date)}:', markup=markup)


async def get_plans_command(message: types.Message):
    await message.delete()
    await bot.send_chat_action(message.from_user.id, 'upload_document')
    str_date = f'{next_send_day().day}.{next_send_day().month}.{next_send_day().year}'
    Plan.create_plans_table(str_date)
    await bot.send_document(message.from_user.id,
                            types.FSInputFile('plans.xlsx', f'Планы на {beauty_date(str_date)}.xlsx'))


async def no_access(message: types.Message):
    await message.delete()
    await message.answer('У вас нет доступа к боту!')


async def fullname_message(message: types.Message, user: PlansBotUser):
    if is_command(message):
        await message.reply('Извините нельзя использовать команды! :)')
        return
    user.fullname = message.text
    user.state = 'CHOOSING LOCATION'
    await user.delete_state_message()
    kb = []
    for location in mongo_db["Locations"].find_one({})["list"]:
        kb.append([types.InlineKeyboardButton(text=location, callback_data=f'SET LOCATION - {location}')])
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
    msg = await message.answer(
        f'Ваше ФИО: <code>{user.fullname}</code>\nЕсли вы написали его неправильно то отмените регистрацию и начните её заново перейдя по длинной ссылке ещё раз!\nВыберите из какого вы региона!',
        reply_markup=markup, parse_mode='HTML')
    user.id_of_message_promoter_to_type = msg.message_id
    await message.delete()


async def banned(message: types.Message):
    await message.reply(
        f'Вы были заблокированы для разблокировки передайте ваш ID руководству\nID: <code>{message.from_user.id}</code>',
        parse_mode='HTML')


async def waiting_for_reg_confirmation(message: types.Message):
    await message.reply('Пожалуйста дождитесь подтверждения регистрации!')


async def start_work_date_after_vacation_message(message: types.Message, user: PlansBotUser):
    str_date = message.text
    try:
        date(int(str_date.split('.')[2]), int(str_date.split('.')[1]), int(str_date.split('.')[0]))
    except:
        await message.reply('Дата написана некорректно')
        return
    if date(int(str_date.split('.')[2]), int(str_date.split('.')[1]), int(str_date.split('.')[0])) < date(
            int(user.state.split()[-1].split('.')[2]), int(user.state.split()[-1].split('.')[1]),
            int(user.state.split()[-1].split('.')[0])):
        await message.reply(f'Написанная дата должна быть не раньше даты плана ({user.state.split()[-1]})!')
        return
    if date(int(str_date.split('.')[2]), int(str_date.split('.')[1]), int(str_date.split('.')[0])) > date(
            int(user.state.split()[-1].split('.')[2]), int(user.state.split()[-1].split('.')[1]),
            int(user.state.split()[-1].split('.')[0])) + timedelta(days=30):
        await message.reply(f'Так долго у нас в отпуск не ходят!')
        return
    str_date = f"{int(str_date.split('.')[0])}.{int(str_date.split('.')[1])}.{int(str_date.split('.')[2])}"
    plan_date = user.state.split()[-1]
    await user.delete_state_message()
    user.state = 'NONE'
    if Plan.get_by_date_and_user_id(message.from_user.id, plan_date) is None:
        Plan.create(user.id, f'В отпуске до {str_date}', plan_date)
        await user.send_message(
            f'Спасибо за оставленный план! В дни отпуска я буду автоматически писать <code>В отпуске до {str_date}</code> в ваш план! Если ваши планы поменяются вы всегда можете изменить план командой /send_plan\nХорошего отдыха!')
    else:
        plan = Plan.get_by_date_and_user_id(message.from_user.id,
                                            plan_date)
        plan.text = f'В отпуске до {str_date}'
        await user.send_message(
            f'План успешно отредактирован! В дни отпуска я буду автоматически писать <code>В отпуске до {str_date}</code> в ваш план! Если ваши планы поменяются вы всегда можете изменить план командой /send_plan\nХорошего отдыха!)')
    await message.delete()


async def start_work_date_after_sick_message(message: types.Message, user: PlansBotUser):
    str_date = message.text
    try:
        date(int(str_date.split('.')[2]), int(str_date.split('.')[1]), int(str_date.split('.')[0]))
    except:
        await message.reply('Дата написана некорректно')
        return
    if date(int(str_date.split('.')[2]), int(str_date.split('.')[1]), int(str_date.split('.')[0])) < date(
            int(user.state.split()[-1].split('.')[2]), int(user.state.split()[-1].split('.')[1]),
            int(user.state.split()[-1].split('.')[0])):
        await message.reply(f'Написанная дата должна быть не раньше даты плана ({user.state.split()[-1]})!')
        return
    if date(int(str_date.split('.')[2]), int(str_date.split('.')[1]), int(str_date.split('.')[0])) > date(
            int(user.state.split()[-1].split('.')[2]), int(user.state.split()[-1].split('.')[1]),
            int(user.state.split()[-1].split('.')[0])) + timedelta(days=30):
        await message.reply(f'Это слишком долго, думаю вы выздоровеете быстрее!')
        return
    str_date = f"{int(str_date.split('.')[0])}.{int(str_date.split('.')[1])}.{int(str_date.split('.')[2])}"
    plan_date = user.state.split()[-1]
    await user.delete_state_message()
    user.state = 'NONE'
    if Plan.get_by_date_and_user_id(message.from_user.id, plan_date) is None:
        Plan.create(user.id, f'На больничном до {str_date}', plan_date)
        await user.send_message(
            f'Спасибо за оставленный план! В дни больничного я буду автоматически писать <code>На больничном до {str_date}</code> в ваш план! Если вы выздоровеете раньше и ваши планы поменяются вы всегда можете изменить план командой /send_plan\nВыздоравливайте поскорее!')
    else:
        plan = Plan.get_by_date_and_user_id(message.from_user.id,
                                            plan_date)
        plan.text = f'На больничном до {str_date}'
        await user.send_message(
            f'План успешно отредактирован! В дни больничного я буду автоматически писать <code>На больничном до {str_date}</code> в ваш план! Если вы выздоровеете раньше и ваши планы поменяются вы всегда можете изменить план командой /send_plan\nВыздоравливайте поскорее!')
    await message.delete()


async def cancel_command(message: types.Message, user: PlansBotUser):
    if user.state == 'NONE':
        await user.send_message('Я не просил вас ничего писать :)')
    elif user.state in ['CHOOSING LOCATION', 'CHOOSING SECTION', 'TYPING FULLNAME']:
        PlansBotUser.delete_by_id(user.id)
        await message.answer('Регистрация отменена!')
    elif user.state == 'WAITING FOR REG CONFIRMATION':
        AccessRequest.get_waiting_by_user_id(user.id).cancel()
        await message.answer('Запрос на регистрацию отозван!')
    elif user.state.startswith('EDITING REG '):
        request = AccessRequest.get_waiting_by_user_id(user.id)
        msg = await user.send_message(await request.get_info(True), markup=AccessRequest.editing_keyboard())
        user.state = "WAITING FOR REG CONFIRMATION"
        user.id_of_message_promoter_to_type = msg.message_id
    else:
        user.state = 'NONE'
        await user.send_message('Действие отменено!')
    await message.delete()


async def unban_command(message: types.Message, user: PlansBotUser):
    await message.delete()
    msg = await user.send_message('Пожалуйста напишите ID пользователя которого хотите разблокировать!',
                                  markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                      [types.InlineKeyboardButton(text='ОТМЕНА',
                                                                  callback_data='CANCEL TYPING UNBAN USER ID')]]))
    user.id_of_message_promoter_to_type = msg.message_id
    user.state = 'TYPING UNBAN USER ID'


async def unban_user_id_message(message: types.Message, user: PlansBotUser):
    try:
        is_banned = PlansBotUser.is_banned_by_id(int(message.text))
    except ValueError:
        await message.reply('Вы написали не число!')
        return
    if not is_banned:
        await message.answer(f'Я не нашел заблокированного пользователя с таким ID (<code>{message.text}</code>)',
                             parse_mode='HTML')
        return
    banned_user_fullname = user.get_banned_user_fullname_by_id(int(message.text))
    user.unban(int(message.text))
    await user.delete_state_message()
    user.state = 'NONE'
    await message.delete()
    await message.answer(f'Пользователь <code>{banned_user_fullname}</code> с ID <code>{message.text}</code> разблокирован!',
                         parse_mode='HTML')
    await user.delete_state_message()


async def help_command(message: types.Message, user: PlansBotUser):
    await message.delete()
    await message.answer(user.help_message_text)


async def choose_location(_, user: PlansBotUser):
    await user.send_message('Пожалуйста выберите регион!',
                            reply_to_message_id=user.id_of_message_promoter_to_type)


async def choose_section(_, user: PlansBotUser):
    await user.send_message('Пожалуйста выберите отдел!',
                            reply_to_message_id=user.id_of_message_promoter_to_type)


async def restart_command(message: types.Message):
    await message.delete()
    await message.answer('RESTARTING...')
    import os
    os.system("bash main.sh")


async def emails_command(message: types.Message):
    await message.delete()
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        *[[types.InlineKeyboardButton(text=email.address, callback_data=f'EDIT EMAIL {email.address}')] for email in
          Email.get_all()], [types.InlineKeyboardButton(text="➕ Добавить почту", callback_data='ADD EMAIL')]])
    await message.answer('Все добавленные почты:' if len(markup.inline_keyboard) > 1 else 'Тут ещё нет почт :(',
                         reply_markup=markup)


async def add_email_address_message(message: types.Message, user: PlansBotUser):
    address = message.text
    if not re.fullmatch(Email.regex, address):
        await message.reply('Адрес почты написан некорректно, попробуйте ещё раз!')
        return
    if Email.exists(address):
        await message.reply('Эта почта уже добавлена!')
        return
    await message.delete()
    email = Email.add(address)
    await user.edit_state_message(email.editing_text, email.editing_markup)
    user.state = f'EDITING EMAIL {address}'


async def notify_command(message: types.Message):
    await message.delete()
    await send_notifications()
    await message.answer('SENT')


async def get_user_command(message: types.Message):
    try:
        given_user = PlansBotUser.get_by_id(int(message.text.split()[1]))
        await message.delete()
        markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text='Редактировать', callback_data=f'EDIT USER {given_user.id}')]])
        await message.answer(given_user.get_info(), reply_markup=markup, parse_mode='HTML')
    except IndexError:
        await message.reply(
            'Некорректное использование команды /get\_user\.\n\nЭта команда используется с аргументом, который передаётся через пробел\.\nШаблон использования: `/get\_user <ID>`\nПример: `/get\_user 1358414277`',
            parse_mode='MarkdownV2')
        return
    except ValueError:
        await message.reply(
            'Некорректное значение аргумента\. В качестве аргумента должно передаваться целое число, ID желаемого пользователя\.\n\nЭта команда используется с аргументом, который передаётся через пробел\.\nШаблон использования: `/get\_user <ID>`\nПример: `/get\_user 1358414277`',
            parse_mode='MarkdownV2')
    except UserNotFoundException:
        await message.reply(f'Пользователь с ID: <code>{message.text.split()[1]}</code> не найден.', parse_mode='HTML')


async def new_users_fullname_message(message: types.Message, user: PlansBotUser):
    try:
        user.set_field(int(user.state.split()[-1]), "fullname", message.text)
        user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
        await bot.edit_message_text(chat_id=message.chat.id,
                                    message_id=user.id_of_message_promoter_to_type,
                                    text=user_to_edit.get_info(),
                                    reply_markup=user_to_edit.editing_markup,
                                    parse_mode='HTML')
        user.state = f'EDITING USER {user_to_edit.id}'
        await message.delete()
    except PermissionDeniedException:
        user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
        await message.reply(
            f"К сожалению {user_to_edit.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.")


async def my_data_command(message: types.Message, user: PlansBotUser):
    await message.answer(user.get_info(for_myself=True), parse_mode='HTML')


async def toggle_notifications_command(message: types.Message, user: PlansBotUser):
    if not user.able_to_switch_notifications:
        await message.answer('К сожалению вы не можете управлять оповещениями :(')
    else:
        user.receive_notifications = not user.receive_notifications
        await message.answer(f'Оповещения {"включены" if user.receive_notifications else "отключены"}')
    await message.delete()


async def get_logs_command(message: types.Message):
    await message.delete()
    await message.answer_document(types.FSInputFile('LOG.log', 'Логи.log'))


async def invite_command(message:types.Message):
    await message.delete()
    await message.answer('Чтобы пригласить нового сотрудника либо скопируйте ссылку и отправьте ему, либо воспользуйтесь кнопкой ниже\n\n Ссылка: <code>https://t.me/plans1234bot?start=AAHIYqEo-le_LuKbbrrsXxLMmxwXmKi7zUM</code>',
                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text='Пригласить', switch_inline_query_chosen_chat=types.SwitchInlineQueryChosenChat(query='👆 нажмите на кнопку', allow_user_chats=True, allow_bot_chats=False, allow_channel_chats=False, allow_group_chats=False))]]),
                         parse_mode='HTML')


async def requests_command(message:types.Message):
    await message.delete()
    requests = AccessRequest.get_waiting()
    end: str
    if (len(str(len(requests))) > 1 and str(len(requests))[-2] == "1") or int(str(len(requests))[-1]) > 4 or len(str(len(requests))[-1]) == 0:
        end = "ов"
    elif str(len(requests))[-1] == "1":
        end = ""
    else:
        end = "a"
    await message.answer(f'<b>{len(requests)}</b> запрос{end}, ожидающих ответа',
                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=request.user_fullname, callback_data=f'VIEW REQUEST {request.id}')] for request in requests] + [[types.InlineKeyboardButton(text="↻ Обновить", callback_data="UPDATE REQUESTS")]]),
                         parse_mode='HTML')


async def new_reg_fullname_message(message: types.Message, user: PlansBotUser):
    await message.delete()
    request = AccessRequest.get_waiting_by_user_id(user.id)
    user.fullname = message.text
    request.user_fullname = message.text
    user.state = "WAITING FOR REG CONFIRMATION"
    await user.edit_state_message(await request.get_info(True), markup=AccessRequest.editing_keyboard())


async def switch_holidays_command(message: types.Message):
    switch_holidays_key()
    await message.answer('Режим праздников включён, бот перезапускается...')
    import os
    os.system("bash main.sh")


def reg_handlers():
    router.message.register(no, lambda message: message.chat.type in ['group', 'supergroup'])
    router.message.register(banned, lambda _, is_user_banned: is_user_banned)
    router.message.register(first_start_command, Command('start'),
                            lambda _, user_exists: not user_exists,
                            F.text == '/start AAHIYqEo-le_LuKbbrrsXxLMmxwXmKi7zUM')
    router.message.register(no_access, lambda _, user_exists: not user_exists)
    router.message.register(cancel_command,
                            Command('cancel'),
                            F.content_type == ContentType.TEXT)
    router.message.register(waiting_for_reg_confirmation,
                            StateFilter('WAITING FOR REG CONFIRMATION'))
    router.message.register(choose_location,
                            StateFilter('CHOOSING LOCATION'))
    router.message.register(choose_section,
                            StateFilter('CHOOSING SECTION'))
    router.message.register(choose_location,
                            StateFilter('EDITING REG LOCATION'))
    router.message.register(choose_section,
                            StateFilter('EDITING REG SECTION'))
    router.message.register(place_message,
                            StateFilter('TYPING PLACE ', startswith=True), F.content_type == ContentType.TEXT)
    router.message.register(start_work_date_after_vacation_message,
                            StateFilter('TYPING START WORK DATE AFTER VACATION', startswith=True),
                            F.content_type == ContentType.TEXT)
    router.message.register(start_work_date_after_sick_message,
                            StateFilter('TYPING START WORK DATE AFTER SICK', startswith=True),
                            F.content_type == ContentType.TEXT)
    router.message.register(new_users_fullname_message,
                            StateFilter('EDITING USERS FULLNAME ', startswith=True), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["edit_users_fullname"]})
    router.message.register(add_email_address_message,
                            StateFilter('ADDING EMAIL'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["/emails"]})
    router.message.register(unban_user_id_message,
                            StateFilter('TYPING UNBAN USER ID'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["/unban"]})
    router.message.register(new_reg_fullname_message,
                            StateFilter('EDITING REG FULLNAME'), F.content_type == ContentType.TEXT)
    router.message.register(fullname_message,
                            StateFilter('TYPING FULLNAME'), F.content_type == ContentType.TEXT)
    router.message.register(get_user_command, Command('get_user'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["/get_user"]})
    router.message.register(catalog_command,
                            Command('catalog'),
                            F.content_type == ContentType.TEXT)
    router.message.register(my_data_command,
                            Command('my_data'),
                            F.content_type == ContentType.TEXT)
    router.message.register(toggle_notifications_command,
                            Command('toggle_notifications'),
                            F.content_type == ContentType.TEXT)
    router.message.register(start_command, Command('start'), F.content_type == ContentType.TEXT)
    router.message.register(help_command, Command('help'), F.content_type == ContentType.TEXT)
    router.message.register(send_plan_command, Command('send_plan'), F.content_type == ContentType.TEXT)
    router.message.register(get_logs_command,
                            Command('get_logs'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["/get_logs"]})
    router.message.register(invite_command,
                            Command('invite'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["invite_new_users"]})
    router.message.register(get_plans_command,
                            Command('get_plans'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["/get_plans"]})
    router.message.register(emails_command,
                            Command('emails'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["/emails"]})
    router.message.register(requests_command,
                            Command('requests'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["responder"]})
    router.message.register(restart_command,
                            Command('restart'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["/restart"]})
    router.message.register(switch_holidays_key,
                            Command('restart'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["/restart"]})
    router.message.register(notify_command,
                            Command('notify'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["/notify"]})
    router.message.register(unban_command,
                            Command('unban'), F.content_type == ContentType.TEXT,
                            flags={"required_permissions": ["/unban"]})
    router.message.register(all_messages)

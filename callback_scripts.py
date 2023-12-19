from aiogram.exceptions import TelegramForbiddenError

from admin_permission import permissions
from classes import PlansBotUser, Email
from aiogram import types, F
from classes import Plan
from classes.plans_bot_user import PermissionDeniedException
from create_bot import router, bot
from filters import StateFilter
from mongo_connector import mongo_db
from mytime import beauty_date


async def callback_for_send_plan_button(query: types.CallbackQuery, user: PlansBotUser):
    str_date = query.data.split()[-1]
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='В ОФИСЕ', callback_data=f'SEND IN OFFICE PLAN {str_date}'),
         types.InlineKeyboardButton(text='НА ВЫЕЗДЕ', callback_data=f'SEND PLACE WHERE YOU WILL BE {str_date}')],
        [types.InlineKeyboardButton(text='В  отпуске', callback_data=f'SEND START WORK DATE AFTER VACATION {str_date}')]])
    if Plan.get_by_date_and_user_id(user.id, f'{str_date}') is not None:
        await query.message.edit_text(
            f'Вы редактируете уже написанный план <code>{Plan.get_by_date_and_user_id(user.id, str_date).text}</code> на {beauty_date(str_date)}',
            reply_markup=markup, parse_mode='HTML')
        return
    await query.message.edit_text(f'Выберете где вы будете в {beauty_date(str_date)}:', reply_markup=markup)


async def callback_for_send_in_office_plan_button(query: types.CallbackQuery, user: PlansBotUser):
    str_date = query.data.split()[-1]
    await query.message.edit_text(f'Продуктивной работы! План на {beauty_date(str_date)} сохранён')
    if Plan.get_by_date_and_user_id(user.id, str_date) is None:
        Plan.create(user.id, 'В офисе', str_date)
    else:
        plan = Plan.get_by_date_and_user_id(user.id, str_date)
        plan.text = 'В офисе'


async def callback_for_send_place_button(query: types.CallbackQuery, user: PlansBotUser):
    str_date = query.data.split()[-1]
    msg = await user.send_message(f'Пожалуйста напишите место где вы будете в {beauty_date(str_date)}!',
                                  markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                      [types.InlineKeyboardButton(text='<< НАЗАД >>',
                                                                  callback_data=f'CANCEL TYPING PLACE {str_date}')]]))
    user.id_of_message_promoter_to_type = msg.message_id
    user.state = f'TYPING PLACE {str_date}'
    await query.message.delete()


async def no_access(query: types.CallbackQuery):
    await query.answer('У вас нет доступа к боту!', True)


async def callback_for_cancel_typing_place_button(query: types.CallbackQuery, user: PlansBotUser):
    user.state = 'NONE'
    await callback_for_send_plan_button(query, user)


async def callback_for_cancel_typing_start_work_date_button(query: types.CallbackQuery, user: PlansBotUser):
    user.state = 'NONE'
    await callback_for_send_plan_button(query, user)


async def callback_for_cancel_typing_ban_user_id_button(query: types.CallbackQuery, user: PlansBotUser):
    user.state = 'NONE'
    await query.answer('Написание ID пользователя для блокировки отменено!', True)
    await query.message.delete()


async def callback_for_cancel_typing_unban_user_id_button(query: types.CallbackQuery, user: PlansBotUser):
    user.state = 'NONE'
    await query.answer('Написание ID пользователя для разблокировки отменено!', True)
    await query.message.delete()


async def typing_fullname(query: types.CallbackQuery):
    await query.answer('Сначала напишите своё ФИО', True)


async def callback_for_accept_reg_button(query: types.CallbackQuery):
    reg_user = PlansBotUser.get_by_id(int(query.data.split()[-1]))
    if reg_user is None:
        await query.answer('Запрос уже отклонен!', True)
        return
    if reg_user.state != 'WAITING FOR REG CONFIRMATION':
        await query.answer('Запрос уже принят!', True)
        return
    reg_user.state = 'NONE'
    await query.answer('Запрос принят успешно!', True)
    await query.message.delete()
    await query.message.answer(f'Вы приняли запрос доступа к боту от {reg_user.fullname}')
    await reg_user.send_message('Ваш запрос на регистрацию был принят!')
    await reg_user.send_message(
        f'Приветствую вас {reg_user.fullname}!')


async def callback_for_decline_reg_button(query: types.CallbackQuery):
    reg_user = PlansBotUser.get_by_id(int(query.data.split()[-1]))
    if reg_user is None:
        await query.answer('Запрос уже отклонен!', True)
        return
    if reg_user.state != 'WAITING FOR REG CONFIRMATION':
        await query.answer('Запрос уже принят!', True)
        return
    PlansBotUser.delete_by_id(reg_user.id)
    await query.answer('Запрос отклонён успешно!', True)
    await query.message.delete()
    await query.message.answer(f'Вы отклонили запрос доступа к боту от {reg_user.fullname}')
    await reg_user.send_message('Ваш запрос на регистрацию был отклонён!')


async def callback_for_ban_reg_button(query: types.CallbackQuery):
    reg_user = PlansBotUser.get_by_id(int(query.data.split()[-1]))
    if reg_user is None:
        await query.answer('Запрос уже отклонен!', True)
        return
    if reg_user.state != 'WAITING FOR REG CONFIRMATION':
        await query.answer('Запрос уже принят!', True)
        return
    PlansBotUser.ban_by_id(reg_user.id)
    await query.answer('Запрос отклонён успешно!', True)
    await query.message.delete()
    await query.message.answer(
        f'Вы отклонили запрос доступа к боту от {reg_user.fullname}\nВы успешно заблокировали исходящие запросы от {reg_user.fullname}\nID: {reg_user.id}\nЧто бы разблокировать напишите команду /unban')
    await reg_user.send_message(
        f'Ваш запрос на регистрацию был отклонён! Вы были заблокированы для разблокировки передайте ваш ID руководству\nID: {reg_user.id}')


async def banned(query: types.CallbackQuery):
    await query.answer(
        f'Вы были заблокированы для разблокировки передайте ваш ID руководству\nID: {query.from_user.id}', True)


async def waiting_for_reg_confirmation(query: types.CallbackQuery):
    await query.answer('Пожалуйста дождитесь подтверждения регистрации!', True)


async def callback_for_send_start_work_date_button(query: types.CallbackQuery):
    reg_user = PlansBotUser.get_by_id(query.from_user.id)
    if reg_user.state != 'NONE':
        await query.answer('Сначала завершите действие!', True)
        return
    str_date = query.data.split()[-1]
    await query.message.delete()
    msg = await reg_user.send_message(f'Пожалуйста напишите дату выхода на работу в формате ДД.ММ.ГГГГ!',
                                      markup=types.InlineKeyboardMarkup(inline_keyboard=[
                                          [types.InlineKeyboardButton(text='<< НАЗАД >>',
                                                                      callback_data=f'CANCEL TYPING START WORK DATE {str_date}')]]))
    reg_user.id_of_message_promoter_to_type = msg.message_id
    reg_user.state = f'TYPING START WORK DATE {str_date}'


async def callback_for_set_location_buttons(query: types.CallbackQuery, user: PlansBotUser):
    user.state = 'CHOOSING SECTION'
    user.location = query.data.split(' - ')[1]
    await user.delete_state_message()
    kb = []
    for section in mongo_db["Sections"].find_one({})["list"]:
        kb.append([types.InlineKeyboardButton(text=section, callback_data=f'SET SECTION - {section}')])
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
    msg = await query.message.answer(
        f'Ваш регион: <code>{user.location}</code>\nЕсли вы выбрали его неправильно то отмените регистрацию и начните её заново перейдя по длинной ссылке ещё раз!\nВыберите чем вы занимаетесь!',
        reply_markup=markup, parse_mode='HTML')
    user.id_of_message_promoter_to_type = msg.message_id


async def callback_for_set_section_buttons(query: types.CallbackQuery, user: PlansBotUser):
    user.state = 'WAITING FOR REG CONFIRMATION'
    user.section = query.data.split(' - ')[1]
    await bot.send_message(404053217,
                           f'Запрос на доступ к боту от {user.fullname}\nВыбранный регион: {user.location}\nВыбранный отдел: {user.section}\nИнформация об аккаунте в Telegram:\nID: {user.id}\nПолное имя: {query.from_user.full_name}\nUsername: {f"@{query.from_user.username}" if query.from_user.username else "не указан"}',
                           reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                               [types.InlineKeyboardButton(text='Принять', callback_data=f'ACCEPT REG {user.id}'),
                                types.InlineKeyboardButton(text='Отклонить', callback_data=f'DECLINE REG {user.id}')],
                               [types.InlineKeyboardButton(text=f'Заблокировать {query.from_user.full_name}',
                                                           callback_data=f'BAN {user.id}')]]))
    await query.message.answer('Запрос на получение доступа к боту был отправлен!')
    await query.message.delete()


async def choosing_location(query: types.CallbackQuery):
    await query.answer('Сначала выберите регион', True)


async def choosing_section(query: types.CallbackQuery):
    await query.answer('Сначала выберите отдел', True)


async def callback_for_add_email_button(query: types.CallbackQuery, user: PlansBotUser):
    await query.message.delete()
    user.id_of_message_promoter_to_type = (await query.message.answer('Напишите адрес почты!',
                                                                      reply_markup=types.InlineKeyboardMarkup(
                                                                          inline_keyboard=[[
                                                                              types.InlineKeyboardButton(
                                                                                  text='<< Отмена >>',
                                                                                  callback_data='CANCEL ADDING EMAIL')]]))).message_id
    user.state = 'ADDING EMAIL'


async def callback_for_cancel_adding_email_button(query: types.CallbackQuery, user: PlansBotUser):
    user.state = 'NONE'
    await query.answer('Добавление почты отменено!', True)
    from text_scripts import emails_command
    await emails_command(query.message)


async def callback_for_add_location_buttons(query: types.CallbackQuery, user: PlansBotUser):
    if not Email.exists(user.state.split()[-1]):
        await query.answer('Эта почта уже отсутствует в базе почт!', True)
        return
    location = query.data.split(' - ')[1]
    email = Email.get_by_address(user.state.split()[-1])
    if location not in mongo_db["Locations"].find_one({})["list"]:
        await query.answer(f'{location} отсутствует в базе регионов!')
    else:
        email.add_location(location)
    await user.edit_state_message(email.editing_text, email.editing_markup)


async def callback_for_remove_location_buttons(query: types.CallbackQuery, user: PlansBotUser):
    if not Email.exists(user.state.split()[-1]):
        await query.answer('Эта почта уже отсутствует в базе почт!', True)
        return
    location = query.data.split(' - ')[1]
    email = Email.get_by_address(user.state.split()[-1])
    if location not in mongo_db["Locations"].find_one({})["list"]:
        await query.answer(f'{location} отсутствует в базе регионов!')
    else:
        email.remove_location(location)
    await user.edit_state_message(email.editing_text, email.editing_markup)


async def callback_for_set_send_send_all_button(query: types.CallbackQuery, user: PlansBotUser):
    if not Email.exists(user.state.split()[-1]):
        await query.answer('Эта почта уже отсутствует в базе почт!', True)
        return
    email = Email.get_by_address(user.state.split()[-1])
    email.send_all = {"TRUE": True, "FALSE": False}[query.data.split()[-1]]
    await user.edit_state_message(email.editing_text, email.editing_markup)


async def callback_for_edit_email_buttons(query: types.CallbackQuery, user: PlansBotUser):
    if not Email.exists(query.data.split()[-1]):
        await query.answer('Эта почта уже отсутствует в базе почт!', True)
        return
    email = Email.get_by_address(query.data.split()[-1])
    user.id_of_message_promoter_to_type = query.message.message_id
    await user.edit_state_message(email.editing_text, email.editing_markup)
    user.state = f'EDITING EMAIL {email.address}'


async def callback_for_delete_email_button(query: types.CallbackQuery, user: PlansBotUser):
    if not Email.exists(user.state.split()[-1]):
        await query.answer('Эта почта уже отсутствует в базе почт!', True)
        return
    Email.delete_by_address(user.state.split()[-1])
    user.state = 'NONE'
    from text_scripts import emails_command
    await emails_command(query.message)


async def callback_for_end_editing_email_button(query: types.CallbackQuery, user: PlansBotUser):
    if not Email.exists(user.state.split()[-1]):
        await query.answer('Эта почта уже отсутствует в базе почт!', True)
    user.state = 'NONE'
    from text_scripts import emails_command
    await emails_command(query.message)


async def callback_for_edit_user_button(query: types.CallbackQuery, user: PlansBotUser):
    user_to_edit = PlansBotUser.get_by_id(int(query.data.split()[-1]))
    if not user.is_higher(user_to_edit.id):
        await query.answer(
            f"К сожалению {user_to_edit.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.", True)
        return
    is_editing_tuple = user_to_edit.is_editing_by_someone
    if is_editing_tuple.is_editing:
        await query.answer(
            f'В данный момент {is_editing_tuple.who_is_editing.fullname} редактирует этого пользователя, во избежании визуальных конфликтных ситуаций редактирование одново пользователя немколькими другими одновременно запрецено!',
            True)
        await query.message.answer(f'В данный момент {is_editing_tuple.who_is_editing.fullname} редактирует этого пользователя, во избежании визуальных конфликтных ситуаций редактирование одново пользователя немколькими другими одновременно запрецено!\n\nТак как вы имеете больше полномочий, чем {is_editing_tuple.who_is_editing.fullname}, поэтому вы можете прервать его действие!',
                                   reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text='Прервать', callback_data=f'CANCEL EDITING USER {user_to_edit.id} FROM {is_editing_tuple.who_is_editing.id}')]]))
        return
    await query.message.edit_text(text=user_to_edit.get_info(), reply_markup=user_to_edit.editing_markup, parse_mode='HTML')
    user.state = f'EDITING USER {user_to_edit.id}'
    user.id_of_message_promoter_to_type = query.message.message_id


async def callback_for_end_editing_user_button(query: types.CallbackQuery, user: PlansBotUser):
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    user.state = 'NONE'
    await query.message.delete_reply_markup()
    await query.message.edit_text(
        text='Редактирование пользователя завершено, изменения сохранены!\n\nИтог:\n' + user_to_edit.get_info(),
        parse_mode='HTML')


async def callback_for_edit_users_fullname_button(query: types.CallbackQuery, user: PlansBotUser):
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    if not user.is_higher(user_to_edit.id):
        await query.answer(
            f"К сожалению {user_to_edit.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.", True)
        return
    await user.delete_state_message()
    msg = await query.message.answer(
        text=f'Введите новое ФИО для пользователя <code>{user.state.split()[-1]}</code>, {user_to_edit.fullname}',
        parse_mode='HTML',
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text='<< Назад >>', callback_data='CANCEL EDITING USERS FULLNAME')]]))
    user.state = f'EDITING USERS FULLNAME {user.state.split()[-1]}'
    user.id_of_message_promoter_to_type = msg.message_id


async def callback_for_cancel_editing_users_fullname_button(query: types.CallbackQuery, user: PlansBotUser):
    user.state = f'EDITING USER {user.state.split()[-1]}'
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    await query.message.edit_text(text=user_to_edit.get_info(), reply_markup=user_to_edit.editing_markup, parse_mode='HTML')


async def callback_for_set_users_something_buttons(query: types.CallbackQuery, user: PlansBotUser):
    try:
        user.set_field(int(user.state.split()[-1]), query.data.split()[-2], {"TRUE": True, "FALSE": False}[query.data.split()[-1]])
        user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
        await query.message.edit_text(text=user_to_edit.get_info(), reply_markup=user_to_edit.editing_markup, parse_mode='HTML')
    except PermissionDeniedException:
        user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
        await query.answer(f"К сожалению {user_to_edit.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.", True)


async def callback_for_set_users_is_admin_button(query: types.CallbackQuery, user: PlansBotUser):
    try:
        if {"TRUE": True, "FALSE": False}[query.data.split()[-1]]:
            user.promote_to_admin(int(user.state.split()[-1]))
        else:
            user.dismiss_admin(int(user.state.split()[-1]))
        user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
        await query.message.edit_text(text=user_to_edit.get_info(), reply_markup=user_to_edit.editing_markup, parse_mode='HTML')
    except PermissionDeniedException:
        user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
        await query.answer(f"К сожалению {user_to_edit.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.", True)


async def callback_for_ban_user_button(query: types.CallbackQuery, user: PlansBotUser):
    try:
        user.ban(int(user.state.split()[-1]))
        banned_user_fullname = PlansBotUser.get_banned_user_fullname_by_id(int(user.state.split()[-1]))
        user.state = 'NONE'
        await query.message.edit_text(f"Пользователь {banned_user_fullname} c ID {int(user.state    .split()[-1])} успешно заблокирован используйте /unban для разблокировки")
        await query.message.delete_reply_markup()
    except PermissionDeniedException:
        user_to_ban = PlansBotUser.get_by_id(int(query.split()[-1]))
        await query.answer(f"К сожалению {user_to_ban.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.", True)


async def callback_for_edit_users_location_button(query: types.CallbackQuery, user: PlansBotUser):
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    if not user.is_higher(user_to_edit.id):
        await query.answer(
            f"К сожалению {user_to_edit.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.",
            True)
        return
    kb = []
    for location in mongo_db["Locations"].find_one({})["list"]:
        kb.append([types.InlineKeyboardButton(text=location, callback_data=f'SET USERS LOC - {location}')])
    kb.append([types.InlineKeyboardButton(text='<< Назад >>', callback_data='CANCEL EDITING USERS LOCATION')])
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await query.message.edit_text(
        text=f'Выберите новый регион для пользователя <code>{user.state.split()[-1]}</code>, {user_to_edit.fullname}',
        parse_mode='HTML',
        reply_markup=markup)
    user.state = f'EDITING USERS LOCATION {user.state.split()[-1]}'


async def callback_for_set_users_location_buttons(query: types.CallbackQuery, user: PlansBotUser):
    location = query.data.split(' - ')[-1]
    try:
        user.set_field(int(user.state.split()[-1]), "location", location)
    except PermissionDeniedException:
        user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
        await query.answer(
            f"К сожалению {user_to_edit.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.",
            True)
        return
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    user.state = f'EDITING USER {user_to_edit.id}'
    await query.message.edit_text(text=user_to_edit.get_info(), reply_markup=user_to_edit.editing_markup, parse_mode='HTML')


async def callback_for_cancel_editing_users_location_button(query: types.CallbackQuery, user: PlansBotUser):
    user.state = f'EDITING USER {user.state.split()[-1]}'
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    await query.message.edit_text(text=user_to_edit.get_info(), reply_markup=user_to_edit.editing_markup, parse_mode='HTML')


async def callback_for_edit_users_section_button(query: types.CallbackQuery, user: PlansBotUser):
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    if not user.is_higher(user_to_edit.id):
        await query.answer(
            f"К сожалению {user_to_edit.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.",
            True)
        return
    kb = []
    for section in mongo_db["Sections"].find_one({})["list"]:
        kb.append([types.InlineKeyboardButton(text=section, callback_data=f'SET USERS SEC - {section}')])
    kb.append([types.InlineKeyboardButton(text='<< Назад >>', callback_data='CANCEL EDITING USERS SECTION')])
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await query.message.edit_text(
        text=f'Выберите новый отдел для пользователя <code>{user.state.split()[-1]}</code>, {user_to_edit.fullname}',
        parse_mode='HTML',
        reply_markup=markup)
    user.state = f'EDITING USERS SECTION {user.state.split()[-1]}'


async def callback_for_set_users_section_buttons(query: types.CallbackQuery, user: PlansBotUser):
    section = query.data.split(' - ')[-1]
    try:
        user.set_field(int(user.state.split()[-1]), "section", section)
    except PermissionDeniedException:
        user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
        await query.answer(
            f"К сожалению {user_to_edit.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.",
            True)
        return
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    user.state = f'EDITING USER {user_to_edit.id}'
    await query.message.edit_text(text=user_to_edit.get_info(), reply_markup=user_to_edit.editing_markup, parse_mode='HTML')


async def callback_for_cancel_editing_users_section_button(query: types.CallbackQuery, user: PlansBotUser):
    user.state = f'EDITING USER {user.state.split()[-1]}'
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    await query.message.edit_text(text=user_to_edit.get_info(), reply_markup=user_to_edit.editing_markup, parse_mode='HTML')


async def callback_for_cancel_editing_users_admin_permissions_button(query: types.CallbackQuery, user: PlansBotUser):
    user.state = f'EDITING USER {user.state.split()[-1]}'
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    await query.message.edit_text(text=user_to_edit.get_info(), reply_markup=user_to_edit.editing_markup, parse_mode='HTML')


async def callback_for_edit_admin_permissions_button(query: types.CallbackQuery, user: PlansBotUser):
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    await query.message.edit_text(text=user_to_edit.get_admin_permissions_editing_text(list(permissions.keys())[0]),
                                  reply_markup=user_to_edit.get_admin_permissions_editing_markup(list(permissions.keys())[0]),
                                  parse_mode='HTML')
    user.state = f'EDITING USERS ADMIN_PERMISSIONS {user.state.split()[-1]}'


async def callback_for_delete_user_button(query: types.CallbackQuery, user: PlansBotUser):
    try:
        user_to_kick = PlansBotUser.get_by_id(int(user.state.split()[-1]))
        user.kick(user_to_kick.id)
        user.state = 'NONE'
        await query.message.edit_text(f"Пользователь {user_to_kick.fullname} c ID {user_to_kick.id} успешно удалён!")
        await query.message.delete_reply_markup()
    except PermissionDeniedException:
        user_to_ban = PlansBotUser.get_by_id(int(query.split()[-1]))
        await query.answer(f"К сожалению {user_to_ban.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.", True)


async def callback_for_set_users_admin_permission_button(query: types.CallbackQuery, user: PlansBotUser):
    try:
        if {'TRUE': True, 'FALSE': False}[query.data.split()[-1]]:
            user.allow_permission(int(user.state.split()[-1]), query.data.split()[-2])
        else:
            user.restrict_permission(int(user.state.split()[-1]), query.data.split()[-2])
        user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
        await query.message.edit_text(text=user_to_edit.get_admin_permissions_editing_text(query.data.split()[-2]),
                                      reply_markup=user_to_edit.get_admin_permissions_editing_markup(query.data.split()[-2]),
                                      parse_mode='HTML')
    except PermissionDeniedException as exception:
        if 'not owner' in str(exception):
            await query.answer('Вы не владелец, поэтому не можете разрешить кому-то назначать и редактировать администраторов.', True)
        else:
            user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
            await query.answer(
                f"К сожалению {user_to_edit.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права его редактировать.",
                True)


async def callback_for_choose_admin_permission_buttons(query: types.CallbackQuery, user: PlansBotUser):
    user_to_edit = PlansBotUser.get_by_id(int(user.state.split()[-1]))
    await query.message.edit_text(text=user_to_edit.get_admin_permissions_editing_text(query.data.split()[-1]),
                                  reply_markup=user_to_edit.get_admin_permissions_editing_markup(
                                      query.data.split()[-1]),
                                  parse_mode='HTML')


async def callback_for_cancel_editing_user_from_another_user_button(query: types.CallbackQuery, user: PlansBotUser):
    user_who_is_editing = PlansBotUser.get_by_id(int(query.data.split()[-1]))
    user_to_edit = PlansBotUser.get_by_id(int(query.data.split()[-1]))
    if not user.is_higher(user_who_is_editing.id):
        await query.answer(
            f"К сожалению {user_who_is_editing.fullname} имеет больше полномочий, чем вы, поэтому вы не имеете права прерывать его действия.",
            True)
        return
    if str(user_to_edit.id) not in user_who_is_editing.state:
        await query.answer(f'Пользователь {user_who_is_editing.fullname} уже не редактирует пользователя {user_to_edit.fullname}', True)
        return
    user_who_is_editing.state = 'NONE'
    await query.answer('Редактирование успешно прервано!')
    await user_who_is_editing.send_message(f'Редактирование прервано пользователем {user.fullname}')
    await query.message.delete()


async def callback_for_join_button(query: types.CallbackQuery, user_exists: bool):
    if user_exists:
        await query.answer('Вы и так есть в нашей системе, не требуется)', True)
        return

    # if query.data.endswith(str(user.id)):
    #     await query.answer('Это приглашение не для вас, оно от вас)', True)
    #     return

    try:
        await bot.send_message(query.from_user.id, 'Дорогой сотрудник, добро пожаловать в бота OVM group!')
        await bot.send_message(query.from_user.id, 'Пожалуйста отправьте мне своё ФИО! Чтобы отменить регистрацию используйте команду /cancel')
        user = PlansBotUser.reg(query.from_user.id)
        user.state = 'TYPING FULLNAME'
        await query.answer('Вы успешно добавлены, перейдите в бота чтобы зарегистрироваться!', True)
        await bot.edit_message_text('Вы успешно добавлены, перейдите в <a href="tg://resolve?domain=plans12345testbot">бота</a> чтобы зарегистрироваться!',
                                    inline_message_id=query.inline_message_id,
                                    reply_markup=None, parse_mode='HTML')
    except TelegramForbiddenError:
        await query.answer()
        await bot.edit_message_text('Приглашаю Вас присоединиться к боту, менеджеру планов компании OVM Group\n\nБот не может дать вам к нему доступ т.к. вы его заблокировали, разблокируйте <a href="tg://resolve?domain=plans12345testbot">бота</a> чтобы присоединиться!', inline_message_id=query.inline_message_id, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(
                                                                                                                   text='Присоединиться',
                                                                                                                   callback_data=query.data)]]), parse_mode='HTML')


def reg_handlers():
    router.callback_query.register(banned, lambda _, is_user_banned: is_user_banned)
    router.callback_query.register(callback_for_join_button, F.data == 'JOIN')
    router.callback_query.register(no_access, lambda _, user_exists: not user_exists)
    router.callback_query.register(waiting_for_reg_confirmation, StateFilter('WAITING FOR REG CONFIRMATION'))
    router.callback_query.register(typing_fullname,
                                   lambda query: PlansBotUser.get_by_id(query.from_user.id).state == 'TYPING FULLNAME')
    router.callback_query.register(choosing_location, StateFilter('CHOOSING LOCATION'),
                                   lambda query: not query.data.startswith('SET LOCATION - '))
    router.callback_query.register(choosing_section, StateFilter('CHOOSING SECTION'),
                                   lambda query: not query.data.startswith('SET SECTION - '))
    router.callback_query.register(callback_for_send_plan_button,
                                   lambda query: query.data.startswith('SEND PLAN'))
    router.callback_query.register(callback_for_send_in_office_plan_button,
                                   lambda query: query.data.startswith('SEND IN OFFICE PLAN'))
    router.callback_query.register(callback_for_send_place_button,
                                   lambda query: query.data.startswith('SEND PLACE WHERE YOU WILL BE'),
                                   flags={"state_filter": StateFilter('NONE'),
                                          "state_error_message": "Сначала завершите действие!"})
    router.callback_query.register(callback_for_send_start_work_date_button,
                                   lambda query: query.data.startswith('SEND START WORK DATE AFTER VACATION'))
    router.callback_query.register(callback_for_cancel_typing_place_button,
                                   lambda query: query.data.startswith('CANCEL TYPING PLACE'),
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('TYPING PLACE ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не пишете место выездного плана!"})
    router.callback_query.register(callback_for_remove_location_buttons,
                                   lambda query: query.data.startswith('REMOVE LOCATION'),
                                   flags={"required_permissions": ["/emails"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING EMAIL',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете почту!"})
    router.callback_query.register(callback_for_add_location_buttons,
                                   lambda query: query.data.startswith('ADD LOCATION'),
                                   flags={"required_permissions": ["/emails"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING EMAIL',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете почту!"})
    router.callback_query.register(callback_for_set_send_send_all_button,
                                   lambda query: query.data.startswith('SET SEND_ALL'),
                                   flags={"required_permissions": ["/emails"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING EMAIL',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете почту!"})
    router.callback_query.register(callback_for_edit_email_buttons,
                                   lambda query: query.data.startswith('EDIT EMAIL'),
                                   flags={"required_permissions": ["/emails"],
                                          "state_filter": StateFilter('NONE'),
                                          "state_error_message": "Сначала завершите действие!"})
    router.callback_query.register(callback_for_cancel_typing_start_work_date_button,
                                   lambda query: query.data.startswith('CANCEL TYPING START WORK DATE'),
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('TYPING START WORK DATE ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не пишете дату выхода на работу!"})
    router.callback_query.register(callback_for_cancel_typing_ban_user_id_button,
                                   F.data == 'CANCEL TYPING BAN USER ID',
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('TYPING BAN USER ID'),
                                          "state_error_message": "Вы сейчас не пишете ID пользователя для блокировки!"})
    router.callback_query.register(callback_for_cancel_adding_email_button,
                                   F.data == 'CANCEL ADDING EMAIL',
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('ADDING EMAIL'),
                                          "state_error_message": "Вы сейчас не добавляете почту!"})
    router.callback_query.register(callback_for_add_email_button,
                                   F.data == 'ADD EMAIL',
                                   flags={"required_permissions": ["/emails"],
                                          "state_filter": StateFilter('NONE'),
                                          "state_error_message": "Сначала завершите действие!"})
    router.callback_query.register(callback_for_delete_email_button,
                                   F.data == 'DELETE EMAIL',
                                   flags={"required_permissions": ["/emails"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING EMAIL',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете почту!"})
    router.callback_query.register(callback_for_end_editing_email_button,
                                   F.data == 'END EDITING EMAIL',
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('EDITING EMAIL',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете почту!"})
    router.callback_query.register(callback_for_cancel_typing_unban_user_id_button,
                                   F.data == 'CANCEL TYPING UNBAN USER ID',
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('TYPING UNBAN USER ID'),
                                          "state_error_message": "Вы сейчас не пишете ID пользователя для разблокировки!!"})
    router.callback_query.register(callback_for_accept_reg_button,
                                   lambda query: query.data.startswith('ACCEPT REG'))
    router.callback_query.register(callback_for_decline_reg_button,
                                   lambda query: query.data.startswith('DECLINE REG'))
    router.callback_query.register(callback_for_set_location_buttons,
                                   lambda query: query.data.startswith('SET LOCATION - '),
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('CHOOSING LOCATION'),
                                          "state_error_message": "Вы сейчас не выбираете регион!"})
    router.callback_query.register(callback_for_set_section_buttons,
                                   lambda query: query.data.startswith('SET SECTION - '),
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('CHOOSING SECTION'),
                                          "state_error_message": "Вы сейчас не выбираете отдел"})
    router.callback_query.register(callback_for_ban_user_button,
                                   F.data == 'BAN USER',
                                   flags={"required_permissions": ["/ban"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USER ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете пользователя!"})
    router.callback_query.register(callback_for_delete_user_button,
                                   F.data == 'DELETE USER',
                                   flags={"required_permissions": ["/kick"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USER ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете пользователя!"})
    router.callback_query.register(callback_for_ban_reg_button,
                                   lambda query: query.data.startswith('BAN '))
    router.callback_query.register(callback_for_edit_user_button,
                                   lambda query: query.data.startswith('EDIT USER '),
                                   flags={"required_permissions": ["edit_users"],
                                          "state_filter": StateFilter('NONE'),
                                          "state_error_message": "Сначала завершите действие!"})
    router.callback_query.register(callback_for_set_users_is_admin_button,
                                   lambda query: query.data.startswith('SET USERS is_admin '),
                                   flags={"required_permissions": ["choose_admins"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USER ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете пользователя!"})
    router.callback_query.register(callback_for_set_users_something_buttons,
                                   lambda query: query.data.startswith('SET USERS receive_notifications '),
                                   flags={"required_permissions": ["edit_users_notifications"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USER ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете пользователя!"})
    router.callback_query.register(callback_for_set_users_something_buttons,
                                   lambda query: query.data.startswith('SET USERS able_to_switch_notifications '),
                                   flags={"required_permissions": ["edit_users_notifications"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USER ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете пользователя!"})
    router.callback_query.register(callback_for_edit_users_section_button,
                                   F.data == "EDIT USERS SECTION",
                                   flags={"required_permissions": ["edit_users_section"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USER ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете пользователя!"})
    router.callback_query.register(callback_for_edit_users_location_button,
                                   F.data == "EDIT USERS LOCATION",
                                   flags={"required_permissions": ["edit_users_location"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USER ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете пользователя!"})
    router.callback_query.register(callback_for_end_editing_user_button,
                                   F.data == 'END EDITING USER',
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('EDITING USER ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете пользователя!"})
    router.callback_query.register(callback_for_edit_users_fullname_button,
                                   F.data == 'EDIT USERS FULLNAME',
                                   flags={"required_permissions": ["edit_users_fullname"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USER ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете пользователя!"})
    router.callback_query.register(callback_for_set_users_location_buttons,
                                   lambda query: query.data.startswith('SET USERS LOC - '),
                                   flags={"required_permissions": ["edit_users_location"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USERS LOCATION ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не выбираете новый регион для пользователя!"})
    router.callback_query.register(callback_for_set_users_section_buttons,
                                   lambda query: query.data.startswith('SET USERS SEC - '),
                                   flags={"required_permissions": ["edit_users_section"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USERS SECTION ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не выбираете новый отдел для пользователя!"})
    router.callback_query.register(callback_for_set_users_admin_permission_button,
                                   lambda query: query.data.startswith('SET USERS A_P '),
                                   flags={"required_permissions": ["choose_admins"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USERS ADMIN_PERMISSIONS ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете права администратора для пользователя!"})
    router.callback_query.register(callback_for_choose_admin_permission_buttons,
                                   lambda query: query.data.startswith('CHOOSE PERMISSION '),
                                   flags={"required_permissions": ["choose_admins"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USERS ADMIN_PERMISSIONS ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете права администратора для пользователя!"})
    router.callback_query.register(callback_for_cancel_editing_users_fullname_button,
                                   F.data == 'CANCEL EDITING USERS FULLNAME',
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('EDITING USERS FULLNAME ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не пишете новое ФИО для пользователя!"})
    router.callback_query.register(callback_for_cancel_editing_users_location_button,
                                   F.data == 'CANCEL EDITING USERS LOCATION',
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('EDITING USERS LOCATION ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не выбираете новый регион для пользователя!"})
    router.callback_query.register(callback_for_cancel_editing_users_admin_permissions_button,
                                   F.data == 'CANCEL EDITING ADMIN_PERMISSIONS',
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('EDITING USERS ADMIN_PERMISSIONS ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете права администратора для пользователя!"})
    router.callback_query.register(callback_for_cancel_editing_users_section_button,
                                   F.data == 'CANCEL EDITING USERS SECTION',
                                   flags={"check_state_message": True,
                                          "state_filter": StateFilter('EDITING USERS SECTION ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не выбираете новый отдел для пользователя!"})
    router.callback_query.register(callback_for_edit_admin_permissions_button,
                                   F.data == 'EDIT USERS ADMIN_PERMISSIONS',
                                   flags={"required_permissions": ["choose_admins"],
                                          "check_state_message": True,
                                          "state_filter": StateFilter('EDITING USER ',
                                                                      startswith=True),
                                          "state_error_message": "Вы сейчас не редактируете пользователя!"})
    router.callback_query.register(callback_for_cancel_editing_user_from_another_user_button,
                                   lambda query: query.data.split("CANCEL EDItiNG USER "))

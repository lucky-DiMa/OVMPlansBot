from datetime import date
from mailing_client.mail_sender import send_table
from aiogram import types
from classes import PlansBotUser, Plan, Email
from create_bot import bot
from utils import next_send_day, today, beauty_date


async def send_notifications():
    str_date = f'{next_send_day().day}.{next_send_day().month}.{next_send_day().year}'
    markup = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text='Написать!', callback_data=f'SEND PLAN {str_date}')]])
    str_today = f'{today().day}.{today().month}.{today().year}'
    for user in PlansBotUser.get_users_that_not_sent_plans(next_send_day()):
        if user.state in ['CHOOSING LOCATION', 'CHOOSING SECTION', 'TYPING FULLNAME', 'WAITING FOR REG CONFIRMATION']:
            continue
        if Plan.get_by_date_and_user_id(user.id, str_today) and (Plan.get_by_date_and_user_id(user.id,
                                                                                             str_today).text.startswith(
                'В отпуске до ') or Plan.get_by_date_and_user_id(user.id,
                                                                                             str_today).text.startswith(
                'На больничном до ')):
            str_start_work_date = Plan.get_by_date_and_user_id(user.id, str_today).text.split()[-1]
            if next_send_day() < date(int(str_start_work_date.split('.')[2]), int(str_start_work_date.split('.')[1]),
                                      int(str_start_work_date.split('.')[0])):
                Plan.create(user.id, Plan.get_by_date_and_user_id(user.id, str_today).text, str_date)
                continue
        if not user.receive_notifications:
            continue
        await user.send_message(
            f'Пожалуйста напишите свой план на {"завтра" if today().isoweekday() != 5 else "понедельник"}!',
            markup=markup)


async def mailing():
    for email in Email.get_all():
        Plan.create_plans_table(f'{next_send_day().day}.{next_send_day().month}.{next_send_day().year}', email.locations)
        send_table(email.address)


async def send_plans_table():
    Plan.create_plans_table(f'{next_send_day().day}.{next_send_day().month}.{next_send_day().year}')
    await bot.send_document(404053217, types.FSInputFile('../plans.xlsx',
                                                       f'Планы на {beauty_date(f"{next_send_day().day}.{next_send_day().month}.{next_send_day().year}")}.xlsx'))

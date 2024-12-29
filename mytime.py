from datetime import timedelta, datetime, timezone, date


days_of_week = [('понедельник', 'понедельник'),
                ('вторник','вторник'),
                ('среду', 'среда'),
                ('четверг','четверг'),
                ('пятницу', 'пятница'),
                ('субботу', 'суббота'),
                ('воскресенье', 'воскресенье')]
months = ['января',
          'февраля',
          'марта',
          'апреля',
          'мая',
          'июня',
          'июля',
          'августа',
          'сентября',
          'октября',
          'ноября',
          'декабря']


def beauty_date(date_: str | date, mode: int = 0):
    """
    :param mode: 0 - день недели в Р.П. 1 - день недели в И.П.
    """
    if type(date_) is str:
        return f'{days_of_week[date(int(date_.split(".")[2]), int(date_.split(".")[1]), int(date_.split(".")[0])).weekday()][mode]}, {date_.split(".")[0]} {months[int(date_.split(".")[1]) - 1]} {date_.split(".")[2]} года'
    return f'{days_of_week[date_.weekday()][mode]}, {date_.day} {months[date_.month - 1]} {date_.year} года'


def beauty_datetime(datetime_: datetime, mode: int = 0):
    """
    :param mode: 0 - день недели в Р.П. 1 - день недели в И.П.
    """
    return f'{datetime_.hour}:{"0" if len(str(datetime_.minute)) == 1 else ""}{datetime_.minute}, {days_of_week[datetime_.weekday()][mode]}, {datetime_.day} {months[datetime_.month - 1]} {datetime_.year} года'


def now_time():
    return datetime.now(timezone(timedelta(hours=5)))


def today():
    return datetime.now(timezone(timedelta(hours=5))).date()


def next_send_day():
    if today().isoweekday() < 5:
        return today() + timedelta(days=1)
    return today() + timedelta(days=8-today().isoweekday())

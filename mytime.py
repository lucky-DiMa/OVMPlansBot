from datetime import timedelta, datetime, timezone, date


days_of_week = ['понедельник',
                'вторник',
                'среду',
                'четверг',
                'пятницу']
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


def beauty_date(date_: str | date):
    if type(date_) is str:
        return f'{days_of_week[date(int(date_.split(".")[2]), int(date_.split(".")[1]), int(date_.split(".")[0])).weekday()]}, {date_.split(".")[0]} {months[int(date_.split(".")[1]) - 1]} {date_.split(".")[2]} года'
    return f'{days_of_week[date_.weekday()]}, {date_.day} {months[date_.month - 1]} {date_.year} года'


def now_time():
    return datetime.now(timezone(timedelta(hours=5)))


def today():
    return datetime.now(timezone(timedelta(hours=5))).date()


def next_send_day():
    if today().isoweekday() < 5:
        return today() + timedelta(days=1)
    return today() + timedelta(days=8-today().isoweekday())

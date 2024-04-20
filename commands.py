from typing import NamedTuple


class Command(NamedTuple):
    explanation: str
    required_permissions: list[str] = []


commands = {'/send_plan': Command('Отправить план на завтра или понедельник (если сегодня пятница)'),
            '/catalog': Command('Открыть каталог'),
            '/my_data': Command('Вся информация о вас, которую я храню'),
            '/toggle_notifications': Command('Включить/выключить оповещения'),
            '/cancel': Command('Отменить ввод информации'),
            '/get_plans': Command('Получить планы на завтра или понедельник (если сегодня пятница)', ['/get_plans']),
            '/emails': Command('Список добавленных почт', ['/emails']),
            '/notify': Command('Разослать уведомления', ['/notify']),
            '/invite': Command('Пригласить нового сотрудника', ['invite_new_users']),
            '/restart': Command('Программный перезапуск бота', ['/restart']),
            '/get_user': Command('Информация о пользователе и интерфейс для его редактирования по ID', ['/get_user']),
            '/unban': Command('Разблокировать пользователя по ID', ['/unban']),
            '/get_logs': Command('Файл с логами программных ошибок', ['/get_logs']),
            '/edit_catalog': Command('Изменить каталог', ['/edit_catalog']),
            '/get_users': Command('Таблица с информацией о всех пользователях (В разработке)', ['/get_users']),
            '/get_banned_users': Command('Таблица с информацией о всех заблокированных пользователях (В разработке)', ['/get_banned_users']),
            '/get_admins': Command('Таблица с информацией о всех администраторах (В разработке)', ['/get_admins']),
            '/edit_regions': Command('Добавление новых регионов и удаление существующих (В разработке)', ['/edit_regions']),
            '/edit_sections': Command('Добавление новых отделов и удаление существующих (В разработке)', ['/edit_sections'])}
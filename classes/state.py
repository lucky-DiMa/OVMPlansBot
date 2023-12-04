class State:
    states = {"WAITING FOR REG CONFIRMATION": "Ожидает подтверждения регистрации",
              "TYPING FULLNAME": "Пишет ФИО",
              "СHOOSING SECTION": "Выбирает отдел",
              "CHOOSING REGION": "Выбирает регион",
              "TYPING PLACE": "Пишет место (план на {subject})",
              "TYPING START WORK DATE": "Пишет дату окончания отпуска (план на {subject}",
              "TYPING UNBAN USER ID": "Пишет ID пользователя для разблокировки",
              "ADDING EMAIL": "Пишет адрес новой эл. почты (добавляет эл.почту)",
              "EDITING EMAIL": "Изменяет листы таблицы для почты {subject}",
              "EDITING USER": "Редактирует пользователя {subject}",
              "EDITING USERS FULLNAME": "Редактирует ФИО пользователя {subject}",
              "EDITING USERS LOCATION": "Редактирует регион пользователя {subject}",
              "EDITING USERS SECTION": "Редактирует отдел пользователя {subject}",
              "EDITING USERS ADMIN_PERMISSIONS": "Редактирует права администратора пользователя {subject}",
              "NONE": "Бездействует"}

    def __init__(self):
        del self
        raise Exception('NOT CREATABLE CLASS')

    @classmethod
    def get_explanation(cls, state: str):
        if state[-1] in '1234567890' or '@' in state:
            return cls.states[' '.join(state.split()[:-1])].format(subject=state.split()[-1])
        return cls.states[state]

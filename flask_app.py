import asyncio
import json
from datetime import datetime

import aiohttp

import config
from classes import Session, PlansBotUser, CatalogItem, SendMessageAction


def create_table(info: dict):
    if not info["lessons"]:
        return "Сегодня нет уроков"

    def auditory_converter(s: str):
        if s == 'Нет':
            return ''
        elif (e := s.find('-')) == -1:
            return s
        return f'ин{s[e + 1:]}'

    ext, e_str = [['', '', ''] for _ in range(7)], ['' for _ in range(7)]
    for lesson in info['lessons']:
        ext[lesson["number"] - 1][
            lesson["subgroup"]] = f'{lesson["subject"][:10]} в аудитории {auditory_converter(lesson["auditory"][:8]) if auditory_converter(lesson["auditory"][:8]) != "" else "неизвестно"}' if 'нет' not in lesson['subject'].lower() else 'Ничего нет'
    for lesson in info['diffs']:
        if lesson["subgroup"] == 0:
            ext[lesson["number"] - 1][1] = ''
            ext[lesson["number"] - 1][2] = ''
        else:
            ext[lesson["number"] - 1][0] = ''
        ext[lesson["number"] - 1][lesson["subgroup"]]
        ext[lesson["number"] - 1][
            lesson["subgroup"]] = f'{lesson["subject"][:10]} в аудитории {auditory_converter(lesson["auditory"][:8]) if auditory_converter(lesson["auditory"][:8]) != "" else "неизвестно"}' if 'нет' not in lesson['subject'].lower() else 'Ничего нет'
    for i, lesson in enumerate(ext):
        if lesson[0]:
            e_str[i] = lesson[0]
        elif lesson[1] and lesson[2]:
            e_str[i] = f'У первой группы {lesson[1]}, у второй группы {lesson[2]}'
        elif lesson[1]:
            e_str[i] = f'У первой группы {lesson[1]}, у второй группы ничего нет.'
        elif lesson[2]:
            e_str[i] = f'У первой группы ничего нет, у второй группы {lesson[2]}.'
    return '\n'.join([f'Урок {i+1}: {lesson}' for i, lesson in enumerate(e_str)])


def get_weekday(_day: int):
    return ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье")[_day % 7]


async def get_json(weekday: int, group: int):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        async with session.get(
                f'https://lyceum.urfu.ru/ucheba/raspisanie-zanjatii?type=11&scheduleType=group&{weekday=}&{group=}'
        ) as resp:
            return json.loads(await resp.text())


async def main(wd: int = datetime.today().weekday()):
    return create_table(await get_json(wd + 1, 2))


from flask import Flask, request, json, render_template, sessions, make_response, jsonify

app = Flask(__name__)


def handle_dialog(res, req):
    try:
        if not req['request'].get('original_utterance') and not req['request'].get('command') and not req["session"]["new"]:
            raise Exception()
        elif 'на сегодня' in (str(req['request'].get('original_utterance')) + str(req['request'].get('command'))).lower():
            res.get('response').setdefault('text', f'Расписание на сегодня, {get_weekday(datetime.today().weekday())}\n' + asyncio.run(main()))
        elif 'на завтра' in (str(req['request'].get('original_utterance')) + str(req['request'].get('command'))).lower():
            res.get('response').setdefault('text', f'Расписание на завтра, {get_weekday(datetime.today().weekday() + 1)}\n' + asyncio.run(main((datetime.today().weekday() + 1) % 7)))
        elif req["session"]["new"]:
            res.get('response').setdefault('text', "Привет, вы открыли мой прекрасный навык с помошью которого можете узнавать своё расписание и не только, попробуйте сказать 'Алиса, Расписание на завтра'")
        elif 'помощь' in req["request"]["command"] or "что ты умеешь" in req["request"]["command"]:
            res.get('response').setdefault('text', "Вы можете узнавать своё расписание, попробуйте сказать 'Алиса, расписание на завтра' или 'На сегодня'")
        else:
            raise Exception()
    except:
        res.get('response').setdefault('text', "Не понимаю, что вы от меня хотите?")

@app.route('/post', methods=['POST'])
def main2():
    response = {
        'session': request.json.get('session'),
        'version': request.json.get('version'),
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    return json.dumps(response)

@app.route('/')
def index():
    token = request.cookies.get('session_token')
    if not token:
        return render_template('index.html', logged_in=False)
    session = Session.get_by_token(token)
    if not session:
        return render_template('index.html', logged_in=False)
    user = PlansBotUser.get_by_id(session.telegram_id)
    return render_template('index.html', logged_in=True, user=user)

@app.route('/catalog')
def catalog():
    token = request.cookies.get('session_token')
    session = Session.get_by_token(token)
    if not token or not session:
        return render_template('error.html', logged_in=False, message="Вы не вошли в аккаунт!")
    user = PlansBotUser.get_by_id(session.telegram_id)
    if not user.is_allowed("/edit_catalog"):
        return render_template('error.html', logged_in=True, user=user, message="Недостаточно прав!")
    return render_template('catalog.html', logged_in=True, user=user,
                           catalog_items=CatalogItem.get_by_prev_catalog_item_text('main'))


@app.route('/login', methods=['POST'])
def login():
    telegram_id = request.json['telegram_id']
    if not PlansBotUser.exists_by_id(telegram_id):
        return jsonify({"success": False, 'message': "У вас нет доступа к боту!"})
    if not PlansBotUser.registered_by_id(telegram_id):
        return jsonify({"success": False, 'message': "Пройдите регистрацию или дождитесь подтверждения регистрации!"})
    user = PlansBotUser.get_by_id(telegram_id)
    session = Session.create(telegram_id)
    try:
        asyncio.run(user.send_message(f'❗️❗️❗️ Кто-то зашёл в ваш аккаунт на сайте!\nВремя: {datetime.now()}\n\n❗️❗️❗️ Если это были не вы, срочно завершите сессию через команду /sessions'))
    except:
        return jsonify({"success": False, 'message': 'По какой-то причине я не могу написать сообщение о входе на ваш аккаунт в Telegram, в целях безопасности попытка входа была предотвращена!'})
    response = make_response(jsonify({"success": True}))
    response.set_cookie('session_token', session.token)
    return response


@app.route('/logout', methods=['POST'])
def logout():
    Session.end_by_token(request.cookies.get('session_token'))
    response = make_response(jsonify({"ended": True}))
    response.set_cookie('session_token', '', expires=0)
    return response


@app.context_processor
def inject_dict_for_all_templates():
    return {"site_url": config.SITE_URL}


@app.route('/catalog_item', methods=['GET'])
@app.route('/catalog_item', methods=['GET'])
def catalog_item():
    token = request.cookies.get('session_token')
    session = Session.get_by_token(token)
    if not token or not session or not PlansBotUser.get_by_id(session.telegram_id).is_allowed("/edit_catalog"):
        return {'success': False}
    catalog_item_id = int(request.args.get('id'))
    response = CatalogItem.get_by_id(catalog_item_id).to_JSON()
    response['success'] = True
    return jsonify(response)

@app.route('/catalog_item', methods=['UPDATE'])
def catalog_item_upd():
    token = request.cookies.get('session_token')
    session = Session.get_by_token(token)
    if not token or not session or not PlansBotUser.get_by_id(session.telegram_id).is_allowed("/edit_catalog"):
        return {'success': False}
    catalog_item_id = int(request.args.get('id'))
    c_i = CatalogItem.get_by_id(catalog_item_id)
    for k, v in request.json.items():
        c_i.set_field(k, v)
    return {'success': True}


@app.route('/catalog_items_order', methods=['UPDATE'])
def catalog_items_order_upd():
    token = request.cookies.get('session_token')
    session = Session.get_by_token(token)
    if not token or not session or not PlansBotUser.get_by_id(session.telegram_id).is_allowed("/edit_catalog"):
        return {'success': False}
    return {'success': CatalogItem.reorder_catalog_items_by_prev_catalog_item_text(request.json["order"], "main")}

@app.route('/catalog_item', methods=['DELETE'])
def catalog_item_del():
    token = request.cookies.get('session_token')
    session = Session.get_by_token(token)
    if not token or not session or not PlansBotUser.get_by_id(session.telegram_id).is_allowed("/edit_catalog"):
        return {'success': False}
    CatalogItem.delete_by_id(int(request.args.get('id')))
    return {'success': True}

@app.route('/catalog_item', methods=['CREATE'])
def catalog_item_crt():
    token = request.cookies.get('session_token')
    session = Session.get_by_token(token)
    if not token or not session or not PlansBotUser.get_by_id(session.telegram_id).is_allowed("/edit_catalog"):
        return {'success': False}
    c_i = CatalogItem.create()
    act = SendMessageAction.create(f'Вы нажали на {c_i.text}')
    c_i.add_action(act.id)
    return {'success': True, **c_i.to_JSON()}


@app.route('/action', methods=['GET'])
def action():
    token = request.cookies.get('session_token')
    session = Session.get_by_token(token)
    if not token or not session or not PlansBotUser.get_by_id(session.telegram_id).is_allowed("/edit_catalog"):
        return {'success': False}
    action_id = int(request.args.get('id'))
    response = SendMessageAction.get_by_id(action_id).to_JSON()
    response['success'] = True
    return jsonify(response)

@app.route('/action', methods=['UPDATE'])
def action_upd():
    token = request.cookies.get('session_token')
    session = Session.get_by_token(token)
    if not token or not session or not PlansBotUser.get_by_id(session.telegram_id).is_allowed("/edit_catalog"):
        return {'success': False}
    action_id = int(request.args.get('id'))
    action = SendMessageAction.get_by_id(action_id)
    for k, v in request.json.items():
        action.set_field(k, v)
    return {'success': True}

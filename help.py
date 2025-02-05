import hashlib
import hmac
import time

import aiohttp

from config import TOKEN, RDP_1C_URL


def sort_dict(dict_: dict, by: str, reverse: bool = False):
    sorted_by = reversed(sorted(dict_[by])) if reverse else sorted(dict_[by])
    result = {}
    for key in dict_.keys():
        result[key] = []
    for s in sorted_by:
        i = dict_[by].index(s)
        for key in dict_.keys():
            result[key].append(dict_[key].pop(i))
    return result


def check_telegram_authorization(auth_data: dict):
    check_hash = auth_data.pop('hash')

    # Формирование строки для проверки
    data_check_arr = [f"{key}={value}" for key, value in sorted(auth_data.items())]
    data_check_string = "\n".join(data_check_arr)

    # Генерация секретного ключа и хэша
    secret_key = hashlib.sha256(TOKEN.encode()).digest()
    hash_ = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    # Сравнение хэшей
    if hash_ != check_hash:
        return False

    # Проверка времени авторизации
    if (time.time() - int(auth_data['auth_date'])) > 86400:
        return False

    return auth_data


async def send_find_number_request(number: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(RDP_1C_URL, json={"app":"CRM-mobile",
                                                  "device":"A11 Pro Max",
                                                  "mobile_id":"96822343b76e4f44",
                                                  "operation":"findnumber",
                                                  "useruid":"db68d698-94f5-11ee-94ea-6cb3116585bc",
                                                  "number": number}) as response:
            return await response.json(content_type='text/plain')


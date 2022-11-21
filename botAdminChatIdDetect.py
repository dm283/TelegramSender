import sys, asyncio, configparser
import requests
from cryptography.fernet import Fernet

# загрузка конфигурации
CONFIG_FILE = 'config.ini'
config = configparser.ConfigParser()
config.read(CONFIG_FILE, encoding='utf-8')

# загрузка ключа шифрования
with open('rec-k.txt') as f:
    rkey = f.read().encode('utf-8')
refKey = Fernet(rkey)

hashed_common_bot_token = config['common']['bot_token'].split('\t#')[0]
common_bot_token = (refKey.decrypt(hashed_common_bot_token).decode('utf-8'))

BOT_NAME = config['common']['bot_name'].split('\t#')[0]
BOT_TOKEN = common_bot_token

async def detect_user_chat_id():
# определяет id чата с админом бота
    print('Отправка запроса api.telegram.org на получение событий бота .....')
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates'  # запрос обновлений бота
    try:
        res = requests.get(url).json()
    except Exception as e:
        print('Ошибка: ', e)
        return 1
    if res['ok'] == False:
        print('Получен ответ об ошибке:')
        print(res)
        return 1

    # итерация с конца обновлений к началу
    if 'result' not in res:
        print('Ошибка, получен некорректный ответ, отсутствует поле result.')
        return 1
    for i in range(len(res['result']), 0, -1):
        s = res['result'][i-1]
        if ('message' in s and 'chat' in s['message'] and 'username' in s['message']['chat']
          and s['message']['chat']['username'] == TELEGRAM_USERNAME):
            user_chat_id = s['message']['chat']['id']
            print('user_chat_id:', user_chat_id)
            await save_user_chat_id(str(user_chat_id))
            print(f'ID чата с пользователем telegram {TELEGRAM_USERNAME} сохранен.')
            return 0
    
    print('Ошибка определения id чата. Активируйте бота в telegram (если он не активирован) и/или отправьте ему сообщение.')


async def save_user_chat_id(user_chat_id: str):
    # сохраняет id чата с пользователем username
    config['admin_credentials']['name'] = TELEGRAM_USERNAME + '\t# ' + config['admin_credentials']['name'].split('\t# ')[1]
    config['admin_credentials']['admin_bot_chat_id'] = user_chat_id + '\t# ' + config['admin_credentials']['admin_bot_chat_id'].split('\t# ')[1]
    with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
        config.write(configfile)


# ================================
# приложение запускается с параметром username администратора бота, если он не указан, запрашивается после запуска
if len(sys.argv) == 1:
    TELEGRAM_USERNAME = input('Введите username администратора бота: ')
else:
    TELEGRAM_USERNAME = sys.argv[1]

loop = asyncio.get_event_loop()
loop.run_until_complete(detect_user_chat_id())
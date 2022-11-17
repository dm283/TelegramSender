import sys, asyncio, configparser
import aioodbc, requests

config = configparser.ConfigParser()
config.read('config.ini')

BOT_NAME = config['common']['bot_name']
BOT_TOKEN = config['common']['bot_token']

DB = config['database']['db']  # база данных mssql/posgres
DB_TABLE_GROUPS = config['database']['db_table_groups']  # db.schema.table  таблица с telegram-группами
CONNECTION_STRING = config['database']['connection_string']  # odbc driver system dsn name


async def detect_bot_group():
# определяет id группы после добавления в нее бота
    try:
        cnxn = await aioodbc.connect(dsn=CONNECTION_STRING, loop=loop)
        cursor = await cnxn.cursor()
    except:
        "Подключение к базе данных  -  ошибка"
        return 1
    if await check_bot_group_in_db(cursor):  # проверяет наличие группы бота в бд
        print(f'Параметры группы {GROUP_TITLE} для бота {BOT_NAME} уже записаны в базу данных.')
        await cursor.close()
        await cnxn.close()
        return 0

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

    # итерация с конца обновлений к началу, если бот удален из группы, выводит сообщение и заканчивает итерацию
    if 'result' not in res:
        print('Ошибка, получен некорректный ответ, отсутствует поле result.')
        return 1
    for i in range(len(res['result'])-1, 0, -1):
        s = res['result'][i]
        if 'my_chat_member' in s and s['my_chat_member']['new_chat_member']['status'] == 'left':
            break
        if ('my_chat_member' in s 
            and s['my_chat_member']['chat']['title'] == GROUP_TITLE 
            and s['my_chat_member']['new_chat_member']['status'] == 'member'):
            group_chat_id = int(s['my_chat_member']['chat']['id'])
            print('group_chat_id:', group_chat_id)
            await save_group_params_to_db(BOT_NAME, GROUP_TITLE, group_chat_id, cnxn, cursor)
            print(f'Параметры группы {GROUP_TITLE} для бота {BOT_NAME} записаны в базу данных.')
            return 0
    
    print('Ошибка определения группы. Активируйте бота в telegram (если он не активирован) и/или добавьте в группу.')
    print('Если бот в группе, попробуйте удалить его и добавить заново.')
    await cursor.close()
    await cnxn.close()


async def save_group_params_to_db(BOT_NAME, GROUP_TITLE, group_chat_id, cnxn, cursor):
    # сохраняет параметры группы в базу данных
    try:
        query = f"""insert into {DB_TABLE_GROUPS} (group_title, group_chat_id, bot_name) values (
            '{GROUP_TITLE}', {group_chat_id}, '{BOT_NAME}')"""
        await cursor.execute(query)
        await cnxn.commit()
    except:
        print('Ошибка записи в базу данных.')
        sys.exit()


async def check_bot_group_in_db(cursor):
    # выборка из базы данных
    try:
        query = f"select id from {DB_TABLE_GROUPS} where group_title='{GROUP_TITLE}' and bot_name='{BOT_NAME}'"
        await cursor.execute(query)
        rows = await cursor.fetchall()
    except:
        print('Ошибка чтения из базы данных.')
        sys.exit()
    r = True if len(rows) > 0 else False
    return r


# ================================
# приложение запкускается с параметром название группы, если он не указан, запрашивается после запуска
if len(sys.argv) == 1:
    GROUP_TITLE = input('Введите название группы: ')
else:
    GROUP_TITLE = sys.argv[1]

loop = asyncio.get_event_loop()
loop.run_until_complete(detect_bot_group())
from typing import Union
from pathlib import Path
import subprocess
import traceback
import datetime
import logging
import sqlite3
import random
import time
import json
import sys
import os

# Requires import
try:
    from telebot import types
    import telebot
except:
    try:
        subprocess.check_call(["pip", "install", "-r", "requirements.txt"]) # auto installing requirements
    except:
        print(traceback.format_exc())
        os._exit(0)

    from telebot import types
    import telebot

from messages import *
from config import *


### SCRIPT 1_TELEGRAM_SUB_BOT ###
BASE_DIR = Path(sys.argv[0]).parent
os.chdir(BASE_DIR)
LOGS_DIR = BASE_DIR.joinpath("Logs")
AL_USERS_FILE = BASE_DIR.joinpath("allowed_users.json")


os.makedirs(LOGS_DIR, exist_ok=True)
logs_file = LOGS_DIR.joinpath(datetime.datetime.now().strftime("%d_%m_%Y") + ".log")

logs = os.listdir(LOGS_DIR)
if len(logs) > 15:
    for item in reversed(logs):
        try:
            os.remove(LOGS_DIR.joinpath(item))
        except:
            print(traceback.format_exc())
            continue
logs = []

logger = logging.getLogger()
logging_format = '%(asctime)s : %(name)s : %(levelname)s : %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=logging_format
)
try:
    fh = logging.FileHandler(
        logs_file,
        encoding='utf-8'
    )
except:
    try:
        fh = logging.FileHandler(
            logs_file
        )
    except:
        print(traceback.format_exc())
        os._exit(0)
fh.setFormatter(logging.Formatter(logging_format))
logger.addHandler(fh)


try:
    bot = telebot.TeleBot(
        token=BOT_TOKEN,
        parse_mode='html',
        disable_web_page_preview=True
    )
    me = bot.get_me()
    logger.info(str(me))


    connection = sqlite3.connect("database.db", check_same_thread=False)
    cursor = connection.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS chats (
                            main_id INTEGER,
                            chat_id INTEGER,
                            title TEXT,
                            url TEXT
                    );""")
    connection.commit()
except:
    logger.critical(traceback.format_exc())
    os._exit(0)


checked_today = {}
last_check_date = None



def check_admin(id: int) -> bool:
    """ Проверяет ID в ADMIN_ID. """

    if isinstance(ADMIN_ID, list):
        return id in ADMIN_ID
    else:
        return str(id) == str(ADMIN_ID)


def get_allowed() -> dict:
    """ Возвращает dict из AL_USERS_FILE. """

    if not os.path.exists(AL_USERS_FILE):
        tmp = {"enabled": True, "users": ADMIN_ID}
        write_allowed({"enabled": True, "users": ADMIN_ID})

        return tmp

    with open(AL_USERS_FILE, encoding='utf-8') as file:
        return json.loads(file.read())


def write_allowed(data: dict) -> bool:
    """ Записыват dict в AL_USERS_FILE. Возвращает результат. """

    try:
        with open(AL_USERS_FILE, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False)
    except:
        logger.error(traceback.format_exc())
        return False
    else:
        return True


def is_allowed(id: int) -> bool:
    """ Проверяет возможность человеку добавлять каналы. """

    allowed = get_allowed()
    if not allowed.get("enabled"):
        return True

    return id in allowed.get("users")


def check_chats_limit(main_id: int) -> int:
    """ Возвращает количество доступныъ пользователю добавлений """

    chats = cursor.execute("SELECT COUNT(main_id) FROM chats WHERE main_id = ?;", (main_id,))
    rows = chats.fetchone()

    if rows is None:
        return CHATS_LIMIT
    else:
        rows = rows[0]
        return CHATS_LIMIT - rows


def get_chats(main_id: int) -> list[dict]:
    data = cursor.execute("SELECT * FROM chats WHERE main_id = ?;", (main_id,))
    rows = data.fetchall()

    if rows is None:
        return []

    results = []
    for item in rows:
        results.append({
            "id": item[1],
            "title": item[2],
            "url": item[3]
        })

    return results


def del_chats(main_id: int) -> bool:
    try:
        cursor.execute("DELETE FROM chats WHERE main_id = ?;", (main_id,))
        connection.commit()
    except:
        logger.error(traceback.format_exc())
        return False
    else:
        return True


def chats_exists(chat_id: int) -> bool:
    """ Проверяет, есть ли в чате каналы, на которые нужно подписаться. """

    data = cursor.execute("SELECT main_id FROM chats WHERE main_id = ?;", (chat_id,))
    data = data.fetchone()

    if data is None:
        return False
    else:
        return True


def append_usernames(main_id: int, usernames: list[str]) -> int:
    chats = get_chats(main_id)
    chats = [item.get("id") for item in chats]

    one_change = False

    already_exist = False
    not_in_chat = False
    no_needed_info = False

    for username in usernames:
        try:
            chat = bot.get_chat(username)
        except:
            logger.error(traceback.format_exc())
            not_in_chat = True
            continue

        if not chat.title:
            no_needed_info = True
            continue

        if chat.id in chats:
            already_exist = True
            continue

        cursor.execute("INSERT INTO chats VALUES (?, ?, ?, ?);", (main_id, chat.id, chat.title, chat.invite_link or f"https://t.me/{username.replace('@', '')}",))
        one_change = True

    if one_change == True:
        connection.commit()
        return 200
    else:
        if already_exist == True:
            return 401
        elif not_in_chat == True:
            return 402
        elif no_needed_info == True:
            return 403

        return 400


def send_logs(id: int):
    if not isinstance(id, int):
        return

    if os.path.exists(logs_file):
        try:
            with open(logs_file, "rb") as file:
                bot.send_document(id, file)
        except:
            logger.error(traceback.format_exc())


def get_cancel_markup() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton(CANCEL_BTN, callback_data="cancel")
    markup.row(item1)

    return markup


def get_admin_markup() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()

    allowed = get_allowed()
    enabled = allowed.get("enabled")
    allowed = None # Очищаем память

    item1 = types.InlineKeyboardButton("Включить whitelist" if enabled == False else "Выключить whitelist", callback_data=f"change_allowed|{1 if enabled == False else 2}")
    item2 = types.InlineKeyboardButton("Список", callback_data="list_whitelist")
    item3 = types.InlineKeyboardButton("Добавить по ID", callback_data="enter_id")
    item4 = types.InlineKeyboardButton("Добавить контакт", callback_data="choose_contact")
    item5 = types.InlineKeyboardButton("Удалить ID", callback_data="enter_id_del")
    markup.row(item1, item2)
    markup.row(item3, item4)
    markup.row(item5)

    return markup


@bot.message_handler(commands=["cancel"], chat_types=["private"])
def cancel_message(message: types.Message):
    try:
        bot.clear_step_handler_by_chat_id(message.chat.id)
    except:
        logger.error(traceback.format_exc())

    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, OPERATION_CANCELED, reply_markup=markup)


@bot.message_handler(commands=['get_logs', 'logs', 'log'], chat_types=['private'])
def logs_command(message: types.Message):
    if not check_admin(message.from_user.id):
        return

    send_logs(message.from_user.id)


@bot.message_handler(commands=["help"], chat_types=["supergroup", "group"])
def help_command(message: types.Message):
    user_allowed = is_allowed(message.from_user.id)
    if not user_allowed:
        try:
            bot.send_message(message.chat.id, START_MESSAGE_CONTINUE_2)
        except:
            logger.error(traceback.format_exc())
        return

    bot.send_message(message.chat.id, COMMANDS_MESSAGE)


@bot.message_handler(commands=["clear"], chat_types=["supergroup", "group"])
def clear_command(message: types.Message):
    if message.from_user and message.from_user.id:
        user_allowed = is_allowed(message.from_user.id)
        if not user_allowed:
            bot.send_message(message.chat.id, START_MESSAGE_CONTINUE_2)
            return

        member_info = bot.get_chat_member(message.chat.id, message.from_user.id)
        if not member_info.status in ["creator", "administrator"]:
            try:
                bot.send_message(message.chat.id, START_MESSAGE_CONTINUE_2, reply_to_message_id=message.id)
            except:
                logger.error(traceback.format_exc())
            return

    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton("Да", callback_data=f'clear_command|{message.chat.id}')
    item2 = types.InlineKeyboardButton("Нет", callback_data=f'cancel')
    markup.row(item1, item2)

    bot.send_message(message.chat.id, SURE_TO_DEL, reply_markup=markup, parse_mode='html')


@bot.message_handler(commands=["status"], chat_types=["supergroup", "group"])
def status_command(message: types.Message):
    if message.from_user and message.from_user.id:
        user_allowed = is_allowed(message.from_user.id)
        if not user_allowed:
            try:
                bot.send_message(message.chat.id, START_MESSAGE_CONTINUE_2)
            except:
                logger.error(traceback.format_exc())
            return

        member_info = bot.get_chat_member(message.chat.id, message.from_user.id)
        if not member_info.status in ["creator", "administrator"]:
            try:
                bot.send_message(message.chat.id, START_MESSAGE_CONTINUE_2, reply_to_message_id=message.id)
            except:
                logger.error(traceback.format_exc())
            return

    chats = get_chats(message.chat.id)

    chats_text = ""
    for item in chats:
        tmp = f" - <a href='{item.get('url')}'>{item.get('title')}</a>"
        if not chats_text:
            chats_text = tmp
        else:
            chats_text += "\n" + tmp

    if not chats_text:
        chats_text = "<i>пусто</i>"

    text = STATUS_MESSAGE.format(chats=chats_text)
    bot.send_message(message.chat.id, text, parse_mode='html', disable_web_page_preview=True)


@bot.message_handler(commands=["kanal"], chat_types=["supergroup", "group"])
def kanal_command(message: types.Message):
    if message.from_user and message.from_user.id:
        user_allowed = is_allowed(message.from_user.id)
        if not user_allowed:
            try:
                bot.send_message(message.chat.id, START_MESSAGE_CONTINUE_2, reply_to_message_id=message.id)
            except:
                logger.error(traceback.format_exc())
            return

        member_info = bot.get_chat_member(message.chat.id, message.from_user.id)
        if not member_info.status in ["creator", "administrator"]:
            try:
                bot.send_message(message.chat.id, START_MESSAGE_CONTINUE_2, reply_to_message_id=message.id)
            except:
                logger.error(traceback.format_exc())
            return

    try:
        logger.debug(f"New kanal command:   from_user: {message.from_user.id if message.from_user else None} chat_id: {message.chat.id}")
    except:
        logger.error(traceback.format_exc())

    usernames = [item.replace("https://t.me/", "@") for item in message.text.split(" ") if item.startswith("@") or item.startswith("https://t.me/")]
    if not usernames:
        try:
            bot.send_message(message.chat.id, ERROR_TO_ADD_NEED_A_LIST, reply_to_message_id=message.id)
        except:
            logger.error(traceback.format_exc())
        return

    can_add = check_chats_limit(message.chat.id)
    if can_add <= 0 or len(usernames) > can_add:
        try:
            bot.send_message(message.chat.id, ERROR_CHATS_LIMIT.format(chats_limit=CHATS_LIMIT), reply_to_message_id=message.id)
        except:
            logger.error(traceback.format_exc())
        return

    results = append_usernames(message.chat.id, usernames)

    if results == 200:
        bot.send_message(message.chat.id, SUCCESSFULLY_ADDED_CHANNELS, reply_to_message_id=message.id)
    elif results == 401:
        bot.send_message(message.chat.id, ERROR_ALREADY_EXIST, reply_to_message_id=message.id)
    elif results == 402:
        bot.send_message(message.chat.id, ERROR_NOT_IN_CHAT, reply_to_message_id=message.id)
    elif results == 403:
        bot.send_message(message.chat.id, ERROR_NO_CHAT_INFO, reply_to_message_id=message.id)
    else:
        bot.send_message(message.chat.id, ERROR, reply_to_message_id=message.id)


@bot.message_handler(commands=["start", "menu"], chat_types=["private"])
def start_message(message: types.Message):
    markup = types.InlineKeyboardMarkup()

    user_allowed = is_allowed(message.from_user.id)

    if user_allowed == True:
        item1 = types.InlineKeyboardButton(ADD_BOT_CHAT, url=f'https://t.me/{me.username}?startgroup=start')
        item2 = types.InlineKeyboardButton(ADD_BOT_CHANNEL, url=f'https://t.me/{me.username}?startchannel=start')
        item3 = types.InlineKeyboardButton(HOW_TO_USE, callback_data="how_to_use")
        markup.row(item1, item2)
        markup.row(item3)

    if check_admin(message.from_user.id):
        item_extra_1 = types.InlineKeyboardButton("Админ панель: Доступность", callback_data=f"admin_panel")
        markup.row(item_extra_1)

    name = message.from_user.first_name or message.from_user.last_name or message.from_user.username
    if message.from_user.first_name:
        name = name.capitalize()
    elif message.from_user.last_name:
        name = name.capitalize()

    if message.from_user.username:
        name = f"<a href='https://t.me/{message.from_user.username}'>{name}</a>"

    bot.send_message(message.chat.id, START_MESSAGE.format(name=name, username=me.username, contin=START_MESSAGE_CONTINUE_1 if user_allowed else START_MESSAGE_CONTINUE_2), reply_markup=markup, parse_mode='html')


@bot.message_handler(func=lambda m: True)
def all_texts_handler(message: types.Message):
    global checked_today, last_check_date

    if message.is_automatic_forward == True:
        logger.debug(f"message [{message.id}] is automatic forwarded")
        return

    if last_check_date and last_check_date.day != datetime.datetime.now().day:
        last_check_date = datetime.datetime.now()
        checked_today = {}

    sub_chats = get_chats(message.chat.id)
    if sub_chats:
        if not checked_today.get(message.from_user.id):
            checked_today[message.from_user.id] = {"sub_to": []}

        sub_to = []
        if DONT_CHECK_A_DAY == False:
            sub_to = checked_today[message.from_user.id].get("sub_to") # type: list[int]
            sub_chats = [item for item in sub_chats if not item.get("id") in sub_to] # type: list[dict]

        for data in sub_chats:
            id = data.get("id")
            if not id or not data.get("title") or not data.get("url"):
                continue

            res = None
            try:
                res = bot.get_chat_member(id, message.from_user.id)
            except Exception as ex:
                if "chat not found" in str(ex):
                    res = True
                else:
                    logger.error(traceback.format_exc())
                    res = None

            if not res or (not isinstance(res, bool) and not res.status in ["creator", "member", "administrator"]):
                markup = types.InlineKeyboardMarkup()

                temp = []
                use_temp = len(sub_chats) > 10
                for data in sub_chats:
                    item = types.InlineKeyboardButton(data.get("title"), data.get("url"))
                    if not use_temp:
                        markup.row(item)
                    else:
                        if len(temp) >= 3:
                            markup.row(*temp)
                            temp.clear()
                        temp.append(item)
                if temp:
                    markup.row(*temp)

                name = message.from_user.first_name or message.from_user.last_name or message.from_user.username
                if message.from_user.first_name:
                    name = name.capitalize()
                elif message.from_user.last_name:
                    name = name.capitalize()

                if message.from_user.username:
                    name = f"<a href='https://t.me/{message.from_user.username}'>{name}</a>"

                bot.send_message(message.chat.id, NEED_TO_SUB.format(name=name), reply_markup=markup, reply_to_message_id=message.id)

                try:
                    bot.delete_message(message.chat.id, message.id)
                except:
                    logger.error(traceback.format_exc())
                return
            else:
                sub_to.append(id)

        checked_today[message.from_user.id]["sub_to"] = sub_to


@bot.message_handler(content_types="users_shared")
def user_shared_handler(message: types.Message):
    if not message.users_shared:
        return

    markup = types.ReplyKeyboardRemove()

    if str(message.users_shared.request_id).startswith("444"):
        try:
            user = message.users_shared.users[0]

            allowed = get_allowed()
            users = allowed.get("users") # type: list[int]
            users.append(user.user_id)
            allowed["users"] = users

            write_allowed(allowed)
            allowed = None
            users.clear() # Очищаем память

            bot.send_message(message.chat.id, SUCCESSFULLY_ADDED_ADMIN_ID.format(id=user.user_id), parse_mode='html')
        except Exception as ex:
            logger.error(traceback.format_exc())
            try:
                bot.send_message(message.chat.id, ERROR_NOT_IN_CHAT if "chat not found" in str(ex) else ERROR, reply_markup=markup)
            except:
                logger.error(traceback.format_exc())
            return


@bot.callback_query_handler(func = lambda call: True)
def callback_answer(call: types.CallbackQuery):
    author_id = call.message.chat.id

    if call.data == "cancel":
        try:
            bot.delete_message(author_id, call.message.id)
        except:
            logger.error(traceback.format_exc())
        try:
            bot.clear_step_handler_by_chat_id(author_id)
        except:
            logger.error(traceback.format_exc())

        bot.send_message(author_id, OPERATION_CANCELED)

    elif call.data.startswith("clear_command"):
        main_id = int(call.data.replace("clear_command|", ""))

        try:
            bot.delete_message(author_id, call.message.id)
        except:
            logger.error(traceback.format_exc())

        result = del_chats(main_id)

        if result == True:
            bot.send_message(author_id, ALL_CHATS_DELETED, parse_mode='html')
        else:
            bot.send_message(author_id, ERROR, parse_mode='html')

    elif call.data == "admin_panel":
        if not check_admin(author_id):
            bot.answer_callback_query(call.id, START_MESSAGE_CONTINUE_2)
            return

        try:
            bot.delete_message(author_id, call.message.id)
        except:
            logger.error(traceback.format_exc())

        markup = get_admin_markup()
        bot.send_message(author_id, ADMIN_PANEL_MESSAGE, reply_markup=markup)

    elif call.data.startswith("change_allowed"):
        change_to = call.data.split("|")[1]

        state = False
        if change_to == "1": # Включить
            state = True
        else:
            state = False

        allowed = get_allowed()
        allowed["enabled"] = state
        write_allowed(allowed)
        allowed = None

        markup = get_admin_markup()
        try:
            bot.edit_message_reply_markup(author_id, call.message.id, reply_markup=markup)
        except:
            logger.error(traceback.format_exc())

            try:
                bot.send_message(author_id, ADMIN_PANEL_MESSAGE, reply_markup=markup, parse_mode='html')
            except:
                logger.error(traceback.format_exc())

    elif call.data.startswith("enter_id"):
        if not check_admin(author_id):
            bot.answer_callback_query(call.id, START_MESSAGE_CONTINUE_2)
            return

        try:
            msg = bot.send_message(author_id, ENTER_NEW_ADMIN_ID, parse_mode='html')
            bot.register_next_step_handler(msg, after_admin_id_enter, msg.message_id, call.data.endswith("_del"))
        except:
            logger.error(traceback.format_exc())

            try:
                bot.send_message(author_id, ERROR)
            except:
                logger.error(traceback.format_exc())

    elif call.data == "list_whitelist":
        if not check_admin(author_id):
            bot.answer_callback_query(call.id, START_MESSAGE_CONTINUE_2)
            return

        allowed = get_allowed()
        users = allowed.get("users")
        allowed = None

        users_text = ""
        for item in users:
            tmp = f" - {item}"
            if not users_text:
                users_text = tmp
            else:
                users_text += "\n" + tmp

        if not users_text:
            users_text = "<i>пусто</i>"

        text = LIST_WHITELIST_MESSAGE.format(users=users_text)
        bot.send_message(author_id, text, parse_mode='html', disable_web_page_preview=True)

    elif call.data == "choose_contact":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

        id = int(f"444{random.randint(100, 1000)}")
        item1 = types.KeyboardButton(SELECT_CONTACT, request_user=types.KeyboardButtonRequestUsers(
                                                                                                id,
                                                                                                user_is_bot=False
                                                                                            )
                                    )
        markup.row(item1)

        bot.send_message(author_id, SELECT_CONTACT, reply_markup=markup)

    elif call.data == "how_to_use":
        try:
            bot.send_message(author_id, COMMANDS_MESSAGE)
        except:
            logger.error(traceback.format_exc())

    bot.answer_callback_query(call.id, "Готово!")


def after_admin_id_enter(message: types.Message, edit_id: int, to_del: Union[bool, None] = False):
    entered = message.text

    markup = get_cancel_markup()
    if not entered:
        msg = bot.send_message(message.chat.id, ERROR_NO_TEXT, reply_markup=markup)
        bot.register_next_step_handler(msg, after_admin_id_enter, msg.message_id)
        return

    try:
        entered = int(entered)
    except:
        msg = bot.send_message(message.chat.id, ERROR_NOT_INT, reply_markup=markup)
        bot.register_next_step_handler(msg, after_admin_id_enter, msg.message_id)
        return

    try:
        bot.delete_message(message.chat.id, edit_id)
    except:
        logger.error(traceback.format_exc())
    try:
        bot.delete_message(message.chat.id, message.id)
    except:
        logger.error(traceback.format_exc())

    allowed = get_allowed()
    users = allowed.get("users") # type: list[int]

    if to_del == True:
        if not entered in users:
            msg = bot.send_message(message.chat.id, ERROR_ID_NOT_IN_LIST, parse_mode='html', reply_markup=markup)
            bot.register_next_step_handler(msg, after_admin_id_enter, msg.message_id)
            return

        try:
            users.remove(entered)
        except:
            logger.error(traceback.format_exc())
    else:
        if entered in users:
            msg = bot.send_message(message.chat.id, ERROR_ALREADY_EXIST, parse_mode='html', reply_markup=markup)
            bot.register_next_step_handler(msg, after_admin_id_enter, msg.message_id)
            return

        users.append(entered)
    allowed["users"] = users

    write_allowed(allowed)
    allowed = None
    users.clear() # Очищаем память

    bot.send_message(message.chat.id, SUCCESSFULLY_ADDED_ADMIN_ID.format(id=entered) if to_del == False else SUCCESSFULLY_REMOVED_ADMIN_ID.format(id=entered), parse_mode='html')


# Made by https://kwork.ru/user/juicefw
while True:
    try:
        bot.polling(none_stop=True, interval=0)
    except:
        logger.critical(traceback.format_exc())
        time.sleep(10)

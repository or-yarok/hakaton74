import telebot
from dotenv import load_dotenv
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
import re
# import openai
from yandexgptlite import YandexGPTLite
import csv
from enum import Enum

contracts_csv_filename = "contracts_list.csv"

with open(contracts_csv_filename, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=',')
    contracts =[]
    for row in reader:
        contracts.append(row)

load_dotenv()

# CONSTANTS
TOKEN = os.getenv('TOKEN')
if TOKEN is None:
    raise ValueError({'TOKEN': TOKEN})
BOT_NAME = "@hakaton74_bot"

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
if not YANDEX_API_KEY:
    raise ValueError(
            "No API key found. Please set your YANDEX_API_KEY in the .env file."
        )

YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
if not YANDEX_API_KEY:
    raise ValueError(
            "No FOLDER_ID found. Please set your YANDEX_FOLDER_ID in the .env file."
        )
# MODEL = "lite"


class LANGUAGES(Enum):
    ENG = 'English'
    RUS = 'Russian'
    GEO = 'Georgian'
    CHI = 'Chinese'


DEFAULT_LANG = LANGUAGES.RUS.value  # language by default

LANGUAGES_LIST = tuple(lang.value for lang in LANGUAGES)

# language selection keyboard
reply_kb = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True,
                                             resize_keyboard=True,
                                             row_width=1, )
reply_btn = telebot.types.KeyboardButton
language_buttons = [reply_btn(lang) for lang in LANGUAGES_LIST]
language_kb = reply_kb.add(*language_buttons)

bot = telebot.TeleBot(TOKEN, parse_mode='MarkdownV2')


def escape(text: str) -> str:
    """
    Function for escaping special characters reserved for MarkdownV2

    :param text: str - source string

    :return: str - string with escaped special characters
    """
    escape_chars = r'_[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

# alias for InlineKeyboardButton object
btn = telebot.types.InlineKeyboardButton

# alias for InlineKeyboardMarkup
kb = telebot.types.InlineKeyboardMarkup

User_id = int

form_questions = {'project': 'Чем вы занимаетесь? Расскажите о своей компании. Какое основное преимущество?'\
                            ' Что отличает вас от конкурентов?',
                 'task': 'Какую задачу вы хотите решить? Чего хотите достичь в ближайшем будущем?'\
                         ' Что мешает решению в настоящий момент?',
                 'restrictions': 'Какие у вас ограничения? В какой срок вы хотите видеть решение вашей задачи?'\
                                 ' Каков ваш бюджет?',
                 'contact_info': 'Как мы сможем с вами связаться? Оставьте свой телефон или эл.почту.'
                 }


@dataclass
class User:
   user_id: int
   chat_id: int
   name: str
   language: str = DEFAULT_LANG
   contract_number: Optional[str] = None
   form: Optional[Dict[str, str]] = None


users: Dict[User_id, User] = {}  # dictionary of users


@dataclass
class Question:
    text: str
    buttons: Optional[List[telebot.types.InlineKeyboardButton]]


questions: Dict[str, Question] = {
    "GettingKnow": Question(text="Вы уже являетесь клиентом XPAGE?",
                            buttons=[btn('Да', callback_data="Q01_Y"),
                                     btn('Нет', callback_data="Q01_N")]),
    "ContractNum": Question(text="Пожалуйста, сообщите номер вашего договора с XPAGE",
                            buttons=None),
    "NewUser":     Question(text="Чем я могу вам помочь?",
                            buttons=[btn('Подобрать решение для ваших задач', callback_data='Q02_solution'),
                                     btn('Направить шаблон договора', callback_data="Q02_contract"),
                                     btn('Рассказать о компании XPAGE', callback_data="Q02_about"),
                                     btn('Примеры наших работ', callback_data="Q02_examples"),
                                    ]
                            )

}

client = YandexGPTLite(YANDEX_FOLDER_ID, YANDEX_API_KEY)


def translate(text:str, dist_lang: str, source_lang: str = DEFAULT_LANG) -> str:
    '''
    Translate using AI from source_lang into dist_lang
    :param text:
    :param dist_lang:
    :param source_lang:
    :return: translated text
    '''
    system_prompt = f"Translate the following text from {source_lang} into {dist_lang}."\
           " Give only translation in your reply."
    temperature = '0.3'
    max_tokens=500
    try:
        result = client.create_completion(text, temperature, system_prompt=system_prompt, max_tokens=max_tokens)
    except:
        result = text
    return result

def advice(text:str) -> str:
    '''
    Send a prompt `text` to AI 
    :param text:
    :return: advice
    '''
    text = f"Какие цифровые решения помогут решить следующую задачу: {text}."
    system_prompt = "Дай ответ как консультант IT-компании, которая предлагает цифровые решения "\
                    "для решения бизнес-задач (создание сайтов, мобильных приложений, SEO-оптимизация, машинное " \
                    "обучение). "
    max_tokens = 5000
    temperature = '0.4'
    try:
        result = client.create_completion(text, temperature, system_prompt=system_prompt, max_tokens=max_tokens)
    except Exception as e:
        print(e)
        result = "Проблема с работой ИИ"
    return result


def text_processing(text: str,
                    lang: str = 'Russian',
                    translation_required: bool = True,
                    debug: bool = False) -> str:
    '''
    Text processing: translation if needed and escaping for MarkdownV2
    :param text:
    :param lang:
    :param translation_required:
    :param debug:
    :return: translated and escaped text
    '''
    if debug:
        print(f'source text: {text}')
    if translation_required and lang != DEFAULT_LANG:
        try:
            result = translate(text, lang)
        except Exception as e:
            result = '\n'.join([text, 'Translation is not successful'])
            if debug:
                print(e)
    else:
        result = text
    result = escape(result)
    if debug:
        print(f'resulting text: {result}')
    return result


@bot.message_handler(commands=['start'])
def start_bot(message: telebot.types.Message):
    user_id = message.from_user.id
    print(user_id)
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    if message.from_user.last_name:
        user_name = ' '.join([user_name, message.from_user.last_name])
    if user_id not in users.keys():
        users[user_id] = User(user_id=user_id, chat_id=chat_id, name=user_name, language=DEFAULT_LANG)
    start_message = f'{user_name}, добрый день! Я помогу вам во взаимодействии с компанией XPAGE.'
    start_message = text_processing(start_message, users[user_id].language)
    bot.send_message(chat_id=chat_id, text=start_message)
    getting_know(message)


@bot.message_handler(commands=['assistant'])
def assistant(message: telebot.types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = "Вы можете обсудить вашу задачу с нашим виртуальным ассистентом: t.me/Hakaton74XPage_bot"
    text = text_processing(text, users[user_id].language)
    bot.send_message(chat_id=chat_id, text=text, parse_mode='MarkdownV2')


@bot.message_handler(commands=['description'])
def description(message: telebot.types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = "Наша компания *XPage* специализируется на разработке корпоративных сайтов,"\
           " мобильных приложений и цифровых услуг. Наша область экспертизы - создание профессиональных"\
           " продуктов в сфере информационных технологий для бизнеса в области спорта, промышленности и "\
           " интернет-магазинов."
    text = text_processing(text, users[user_id].language)
    bot.send_message(chat_id=chat_id, text=text, parse_mode='MarkdownV2')


def getting_know(message: telebot.types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = questions['GettingKnow'].text
    text = text_processing(text, users[user_id].language)
    kb_getting_know = telebot.types.InlineKeyboardMarkup(row_width=2)
    kb_getting_know.add(*questions['GettingKnow'].buttons)
    bot.send_message(chat_id=chat_id, text=text, reply_markup=kb_getting_know)


@bot.callback_query_handler(func=lambda query: query.data.startswith("Q01"))
def getting_know_query(query: telebot.types.CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    if query.data[-1:] == "N":
        new_user(query.message, user_id = user_id)
    if query.data[-1:] == "Y":
        ask_contract_number(user_id, chat_id)


def ask_contract_number(user_id, chat_id):
    text = questions['ContractNum'].text
    text = text_processing(text, users[user_id].language)
    msg = bot.send_message(chat_id=chat_id, text=text)
    bot.register_next_step_handler(msg, get_contract_number)


def get_contract_number(message: telebot.types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    contract_number = message.text
    users[user_id].contract_number = contract_number
    text = f'Вы ввели номер договора: {contract_number}'
    text = text_processing(text, users[user_id].language)
    bot.send_message(chat_id=chat_id, text=text)
    contract_number = contract_number.strip()
    for contract in contracts:
        if contract['num'] == contract_number:
            text = f"Статус работы по вашему договору: {contract['status']}"
            text = text_processing(text, users[user_id].language)
            bot.send_message(chat_id=chat_id, text=text)
            break
    else:
        text = 'Проверьте, верно ли вы ввели номер договора. Я не нашёл его в моей базе данных.'
        text = text_processing(text, users[user_id].language)
        bot.send_message(chat_id=chat_id, text=text)


def new_user(message: telebot.types.Message, user_id):
    chat_id = message.chat.id
    text = questions['NewUser'].text
    text = text_processing(text, users[user_id].language)
    kb_new_user = telebot.types.InlineKeyboardMarkup(row_width=1)
    kb_new_user.add(*questions['NewUser'].buttons)
    msg = bot.send_message(chat_id=chat_id, text=text, reply_markup=kb_new_user)


@bot.callback_query_handler(func=lambda query: query.data.startswith("Q02"))
def info_for_new_user(query: telebot.types.CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    result = query.data.split('_')[1]
    if result == "contract":
        text = 'Шаблон договора'
        if users[user_id].language != 'Russian':
            text = translate(text, users[user_id].language)
        bot.send_message(chat_id=chat_id,
                         text = f"<a href='https://telegra.ph/SHablon-dogovora-04-06'>{text}</a>",
                         parse_mode='html')
    if result == "about":
        text = "Наша компания **XPage** специализируется на разработке корпоративных сайтов,"\
               " мобильных приложений и цифровых услуг. Наша область экспертизы - создание профессиональных"\
               " продуктов в сфере информационных технологий для бизнеса в области спорта, промышленности и "\
               " интернет-магазинов."
        text = text_processing(text, users[user_id].language)
        bot.send_message(chat_id=chat_id, text=text, parse_mode='MarkdownV2')
    if result == "examples":
        text = "Мы разработали корпоративные сайты для Хоккейного клуба Трактор, спортивного телеканала Старт, "\
               "федеральной сети ломбардов Фианит-Ломбард, фабрики для производства гофраупаковки и множество других."
        text = text_processing(text, users[user_id].language)
        bot.send_message(chat_id=chat_id, text=text, parse_mode='MarkdownV2')
    if result == "solution":
        text = "Чтобы ваше общение с менеджером было продуктивнее, пожалуйста, ответьте на несколько вопросов."
        text = text_processing(text, users[user_id].language)
        bot.send_message(chat_id=chat_id, text=text)
        text = form_questions['project']
        text = text_processing(text, users[user_id].language)
        msg = bot.send_message(chat_id=chat_id, text=text)
        bot.register_next_step_handler(msg, form_task)


def form_task(message: telebot.types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    # message_id = message.id
    project = message.text
    users[user_id].form = {'project': project}
    # bot.delete_message(chat_id=chat_id, message_id=message_id)
    text = form_questions['task']
    text = text_processing(text, users[user_id].language)
    msg = bot.send_message(chat_id=chat_id, text=text)
    bot.register_next_step_handler(msg, form_restrictions)


def form_restrictions(message: telebot.types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    # message_id = message.id
    task = message.text
    users[user_id].form['task'] = task
    # bot.delete_message(chat_id=chat_id, message_id=message_id)
    text = form_questions['restrictions']
    text = text_processing(text, users[user_id].language)
    msg = bot.send_message(chat_id=chat_id, text=text)
    bot.register_next_step_handler(msg, form_contact_info)


def form_contact_info(message: telebot.types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    # message_id = message.id
    restrictions = message.text
    users[user_id].form['restrictions'] = restrictions
    # bot.delete_message(chat_id=chat_id, message_id=message_id)
    text = form_questions['contact_info']
    text = text_processing(text, users[user_id].language)
    msg = bot.send_message(chat_id=chat_id, text=text)
    bot.register_next_step_handler(msg, form_final)


def form_final(message: telebot.types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    # message_id = message.id
    contact_info = message.text
    users[user_id].form['contact_info'] = contact_info
    # bot.delete_message(chat_id=chat_id, message_id=message_id)
    text = 'Заполненная вами форма будет отправлена менеджерам. С вами свяжутся в ближайшее время.\n'
    text = text_processing(text, users[user_id].language)
    project_description = ''
    contacts = f"*contact info*: {users[user_id].form['contact_info']}"
    for field, content in users[user_id].form.items():
        line = f'*{field}*: {content} \n'
        if field != 'contact_info':
            project_description += line
    text = text + text_processing(project_description+contacts, translation_required= False)
    bot.send_message(chat_id=chat_id, text=text, parse_mode='MarkdownV2')
    text = advice(project_description)
    text = escape(text)
    bot.send_message(chat_id=chat_id, text=text, parse_mode='MarkdownV2')


@bot.message_handler(commands=['lang'])
def select_language(message: telebot.types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if user_id not in users.keys():
        start_bot(message)
    bot.send_message(chat_id=chat_id, text="select preferable language", reply_markup=language_kb)
    bot.register_next_step_handler(message, change_language)


def change_language(message: telebot.types.Message):
    new_language = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.id
    if new_language in LANGUAGES_LIST:
        users[user_id].language = new_language
        bot.delete_message(chat_id=chat_id, message_id=message_id)
        text = f'language {new_language} is set'
        text = escape(text)
        bot.send_message(chat_id=chat_id, text=text, reply_markup=telebot.types.ReplyKeyboardRemove())
    else:
        text = f'I do not know language {new_language} yet, try later.'
        text = escape(text)
        bot.delete_message(chat_id=chat_id, message_id=message_id)
        bot.send_message(chat_id=chat_id, text=text, reply_markup=language_kb)


if __name__ == "__main__":
    bot.infinity_polling()

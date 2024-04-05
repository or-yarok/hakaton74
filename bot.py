import telebot
from dotenv import load_dotenv
import os
from dataclasses import dataclass
from typing import Dict
import re
from openai import OpenAI

load_dotenv()

# CONSTANTS
TOKEN = os.getenv('TOKEN')
if TOKEN is None:
    raise ValueError({'TOKEN': TOKEN})
BOT_NAME = "@hakaton74_bot"

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError(
            "No API key found. Please set your OPENAI_API_KEY in the .env file."
        )
MODEL = "gpt-4"

LANG = "English"  # language by default

LANGUAGES_LIST = (
    'English',
    'Russian',
    'Georgian',
)

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
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

# alias for InlineKeyboardButton object
btn = telebot.types.InlineKeyboardButton

# alias for InlineKeyboardMarkup
kb = telebot.types.InlineKeyboardMarkup

User_id = int

@dataclass
class User:
   user_id: int
   chat_id: int
   name: str
   language: str = "English"

users: Dict[User_id, User] = {}  # dictionary of users

@bot.message_handler(commands=['start'])
def start_bot(message: telebot.types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    if message.from_user.last_name:
        user_name = ' '.join([user_name, message.from_user.last_name])
    users[user_id] = User(user_id=user_id, chat_id=chat_id, name=user_name, language=LANG)
    start_message = f'{user_name}, this chatbot powered by openAI may tell about our products in any language of your choice.'\
                    ' Use commands to change language and to communicate with me.'
    start_message = escape(start_message)
    bot.send_message(chat_id=chat_id, text=start_message)

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

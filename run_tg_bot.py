import json
import logging
import time

from enum import Enum
from textwrap import dedent

import redis

from environs import Env
from telegram import Bot, ReplyKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
)

import quizzes_parser

from bot_logger import BotLogsHandler

logger = logging.getLogger(__file__)


class Step(Enum):
    ANSWER = 1
    QUESTION = 2


def get_answer_notes(chat_id: int) -> (str, str):
    question_notes = json.loads(db.get(chat_id))
    correct_answer = question_notes['Ответ'].lower().strip(' .,:!\'"').replace('ё', 'е')
    answer_notes = '\n'.join(f'{key}: {value}' for key, value in question_notes.items() if key != 'Вопрос')

    return answer_notes, correct_answer


def get_keyboard(chat_id: int) -> ReplyKeyboardMarkup:
    conversations_step = conv_handler.conversations.get((chat_id, chat_id))

    if conversations_step is Step.ANSWER:
        return answer_keyboard
    else:
        return new_question_keyboard


def handle_answer(update: Update, context: CallbackContext) -> Step:
    step = Step.ANSWER
    keyboard = answer_keyboard

    answer_notes, correct_answer = get_answer_notes(update.message.chat.id)
    user_answer = update.message.text.lower().strip(' .,:!\'"').replace('ё', 'е')

    if user_answer != correct_answer:
        answer = 'Ответ неверный 😔\nПодумай ещё 🤔'

    else:
        step = Step.QUESTION
        keyboard = new_question_keyboard

        db.delete(update.message.chat.id)

        answer = dedent('''\
            Урааа! Совершенной верно 👌
            ➕1️⃣ балл
            Вот что у меня есть по вопросу 👇

        ''') + answer_notes

    update.message.reply_text(dedent(answer), reply_markup=keyboard)

    return step


def handle_fallback(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Я тебя не понял...', reply_markup=get_keyboard(update.message.chat.id))


def handle_loss(update: Update, context: CallbackContext):
    answer_notes, _ = get_answer_notes(update.message.chat.id)

    answer = dedent('''
        Бывает...
        Вот что у меня есть по вопросу 👇
        
    ''') + answer_notes

    update.message.reply_text(answer)
    update.message.reply_text('Лови новый вопрос 👇')

    return handle_new_question(update, context)


def handle_my_score(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f'Мой счёт', reply_markup=get_keyboard(update.message.chat.id))


def handle_new_question(update: Update, context: CallbackContext) -> Step:
    question_notes = quizzes_parser.get_question_notes()
    db.set(update.message.chat.id, json.dumps(question_notes))
    update.message.reply_text(question_notes['Вопрос'], reply_markup=answer_keyboard)

    return Step.ANSWER


def send_err(update: Update, context: CallbackContext) -> None:
    logger.error(msg='Exception during message processing:', exc_info=context.error)

    if update.effective_message:
        text = 'К сожалению произошла ошибка в момент обработки сообщения. ' \
               'Мы уже работаем над этой проблемой.'
        update.effective_message.reply_text(text)


def start(update: Update, context: CallbackContext) -> Step:
    if db.get(update.message.chat.id):
        db.delete(update.message.chat.id)

    update.message.reply_text(
        dedent(f'''\
            {update.effective_user.full_name}, будем знакомы - я Бот Ботыч 😍
            Давай сыграем в викторину?!
        '''),
        reply_markup=new_question_keyboard,
    )

    return Step.QUESTION


def main():
    updater = Updater(tg_token)
    dispatcher = updater.dispatcher
    dispatcher.add_error_handler(send_err)
    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')
    logger.setLevel(logging.DEBUG)

    env = Env()
    env.read_env()
    tg_token = env.str('TELEGRAM_BOT_TOKEN')
    admin_tg_token = env.str('TELEGRAM_ADMIN_BOT_TOKEN')
    admin_tg_chat_id = env.str('TELEGRAM_ADMIN_CHAT_ID')
    db_host = env.str('REDIS_HOST')
    db_port = env.int('REDIS_PORT')
    db_password = env.str('REDIS_PASSWORD')

    bot = Bot(tg_token)
    tg_bot_name = f'@{bot.get_me().username}'

    logger.addHandler(BotLogsHandler(
        bot_name=tg_bot_name,
        admin_tg_token=admin_tg_token,
        admin_tg_chat_id=admin_tg_chat_id,
    ))

    new_question_keyboard = ReplyKeyboardMarkup([['Мой счёт', 'Новый вопрос']], resize_keyboard=True)
    answer_keyboard = ReplyKeyboardMarkup([['Мой счёт', 'Сдаться']], resize_keyboard=True)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            Step.ANSWER: [
                MessageHandler(Filters.regex('Сдаться'), handle_loss),
                MessageHandler(Filters.regex('Мой счёт'), handle_my_score),
                CommandHandler('start', start),
                MessageHandler(Filters.text, handle_answer),
            ],
            Step.QUESTION: [
                MessageHandler(Filters.regex('Новый вопрос'), handle_new_question),
                MessageHandler(Filters.regex('Мой счёт'), handle_my_score),
                CommandHandler('start', start)
            ],
        },
        fallbacks=[MessageHandler(Filters.all, handle_fallback)],
    )

    logger.info('Start Telegram bot.')

    while True:
        try:
            db = redis.StrictRedis(
                host=db_host,
                port=db_port,
                password=db_password,
                charset='utf-8',
                decode_responses=True,
            )

            main()

        except Exception as error:
            logger.exception(error)
            time.sleep(60)

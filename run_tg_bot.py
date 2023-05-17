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


def cancel(update: Update, context: CallbackContext) -> ConversationHandler.END:
    try:
        db.delete(update.message.chat.id)
    except TypeError:
        pass

    update.message.reply_text(
        'Пока! Будет скучно - пиши 😏',
        reply_markup=new_question_keyboard,
    )

    return Step.QUESTION


def handle_get_my_score(update: Update, context: CallbackContext):
    conversations_step = conv_handler.conversations.get((update.message.chat.id, update.message.chat.id))

    if conversations_step is Step.ANSWER:
        keyboard = answer_keyboard
    else:
        keyboard = new_question_keyboard
    update.message.reply_text(f'ТЕСТ {conversations_step} - Мой счёт', reply_markup=keyboard)



def handle_surrender(
    update: Update,
    context: CallbackContext,
    answer_notes: str,
):
    answer = dedent('''
        Бывает...
        Вот что у меня есть по вопросу 👇
        
    ''') + answer_notes

    update.message.reply_text(answer)
    update.message.reply_text('Лови новый вопрос 👇')

    return handle_new_question(update, context)


def handle_new_question(update: Update, context: CallbackContext) -> Step:
    question_notes = quizzes_parser.get_question_notes()

    update.message.reply_text(question_notes['Вопрос'], reply_markup=answer_keyboard)
    update.message.reply_text(question_notes['Ответ'], reply_markup=answer_keyboard)
    db.set(update.message.chat.id, json.dumps(question_notes))

    return Step.ANSWER


def handle_answer(update: Update, context: CallbackContext) -> Step:
    try:
        keyboard = answer_keyboard
        question_notes = json.loads(db.get(update.message.chat.id))

        answer_notes = '\n'.join(f'{key}: {value}' for key, value in question_notes.items() if key != 'Вопрос')
        user_answer = update.message.text.lower().strip(' .,:"').replace('ё', 'е')
        correct_answer = question_notes['Ответ'].lower().strip(' .,:"').replace('ё', 'е')
        step = Step.QUESTION

        if user_answer == correct_answer:
            db.delete(update.message.chat.id)
            keyboard = new_question_keyboard
            answer = dedent('''\
                Урааа! Совершенной верно 👌
                ➕1️⃣ балл
                Вот что у меня есть по вопросу 👇
                
            ''') + answer_notes

        elif update.message.text == 'Сдаться':
            db.delete(update.message.chat.id)
            return handle_surrender(update, context, answer_notes)

        else:
            step = Step.ANSWER
            answer = 'Ответ неверный 😔\nПодумай ещё 🤔'

        update.message.reply_text(dedent(answer), reply_markup=keyboard)

        return step

    except TypeError:
        keyboard = new_question_keyboard

        update.message.reply_text('Я тебя не понял...\nНажми нужную кнопку 👇', reply_markup=keyboard)


def start(update: Update, context: CallbackContext) -> Step:
    try:
        db.delete(update.message.chat.id)
    except TypeError:
        pass

    update.message.reply_text(
        dedent(f'''\
            {update.effective_user.full_name}, будем знакомы - я Бот Ботыч 😍
            Давай сыграем в викторину?!
        '''),
        reply_markup=new_question_keyboard,
    )

    return Step.QUESTION


def send_err(update: Update, context: CallbackContext) -> None:
    logger.error(msg='Exception during message processing:', exc_info=context.error)

    if update.effective_message:
        text = 'К сожалению произошла ошибка в момент обработки сообщения. ' \
               'Мы уже работаем над этой проблемой.'
        update.effective_message.reply_text(text)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')
    logger.setLevel(logging.DEBUG)

    env = Env()
    env.read_env()
    tg_token = env.str('TELEGRAM_BOT_TOKEN')
    admin_tg_token = env.str('TELEGRAM_ADMIN_BOT_TOKEN', '')
    admin_tg_chat_id = env.str('TELEGRAM_ADMIN_CHAT_ID', '')
    db_host = env.str('REDIS_HOST')
    db_port = env.int('REDIS_PORT')
    db_password = env.str('REDIS_PASSWORD')

    bot = Bot(tg_token)
    tg_bot_name = f'@{bot.get_me().username}'


    if not admin_tg_token:
        admin_tg_token = tg_token

    logger.addHandler(BotLogsHandler(
        bot_name=tg_bot_name,
        admin_tg_token=admin_tg_token,
        admin_tg_chat_id=admin_tg_chat_id,
    ))

    logger.info('Start Telegram bot.')

    new_question_keyboard = ReplyKeyboardMarkup([['Мой счёт', 'Новый вопрос']], resize_keyboard=True)
    answer_keyboard = ReplyKeyboardMarkup([['Мой счёт', 'Сдаться']], resize_keyboard=True)

    while True:
        try:
            updater = Updater(tg_token)
            dispatcher = updater.dispatcher

            conv_handler = ConversationHandler(
                entry_points=[
                    CommandHandler('start', start),
                    CommandHandler('cancel', cancel),
                    MessageHandler(Filters.text, handle_answer),
                ],
                states={
                    Step.ANSWER: [
                        MessageHandler(Filters.regex('Мой счёт'), handle_get_my_score),
                        MessageHandler(Filters.text, handle_answer),
                    ],
                    Step.QUESTION: [
                        MessageHandler(Filters.regex('Новый вопрос'), handle_new_question),
                        MessageHandler(Filters.regex('Мой счёт'), handle_get_my_score),
                    ],
                },
                fallbacks=[CommandHandler('cancel', cancel)],
            )

            dispatcher.add_error_handler(send_err)
            dispatcher.add_handler(conv_handler)

            db = redis.StrictRedis(
                host=db_host,
                port=db_port,
                password=db_password,
                charset='utf-8',
                decode_responses=True,
            )

            updater.start_polling()
            updater.idle()

        except Exception as error:
            logger.exception(error)
            time.sleep(60)

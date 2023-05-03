import json
import logging
import random
import time

from enum import Enum

from environs import Env
from pathlib import Path
from telegram import Bot, ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
)
import redis_db

from bot_logger import BotLogsHandler


logger = logging.getLogger(__file__)

class Step(Enum):
    QUESTION = 1
    ANSWER = 2
    SURRENDER = 3
    RESULT = 5
    TRASH = 6


def cancel(update: Update, context: CallbackContext) -> ConversationHandler.END:
    db.delete(update.message.chat.id)

    update.message.reply_text(
        'Пока! Будет скучно - пиши 😏',
        reply_markup=new_question_keyboard,
    )

    return ConversationHandler.END


def get_questions() -> dict[str:dict[str:str]]:
    quizzes_path = Path('quiz-questions/quizzes_parser')
    random_quizzes_file_path = random.choice([*quizzes_path.iterdir()])
    questions = json.loads(random_quizzes_file_path.read_text(encoding='UTF-8'))

    return questions


def handle_get_my_score(
        update: Update,
        context: CallbackContext,
        step: Step,
        reply_markup: ReplyKeyboardMarkup,
):
    update.message.reply_text('Тест - Мой счёт', reply_markup=reply_markup)
    return step

def handle_surrender(
        update: Update,
        context: CallbackContext,
        answer_notes: str,
):
    answer = 'Бывает...\n' \
             'Вот что у меня есть по вопросу 👇\n\n' + answer_notes
    update.message.reply_text(answer)
    update.message.reply_text('Лови новый вопрос 👇')
    return handle_new_question(update, context)


def handle_new_question(update: Update, context: CallbackContext) -> Step:
    if update.message.text == 'Мой счёт':
        return handle_get_my_score(
            update=update,
            context=context,
            step=Step.QUESTION,
            reply_markup=new_question_keyboard,
        )

    questions = get_questions()
    random_num = random.randrange(1, len(questions))
    question = questions[str(random_num)].get('Вопрос', '')

    while not question:
        random_num = random.randrange(1, len(questions))
        question = questions[str(random_num)].get('Вопрос', '')

    update.message.reply_text(question, reply_markup=answer_keyboard)
    db.set(update.message.chat.id, str(questions[str(random_num)]))

    return Step.ANSWER


def handle_answer(update: Update, context: CallbackContext) -> Step:
    if update.message.text == 'Мой счёт':
        return handle_get_my_score(
            update=update,
            context=context,
            step=Step.ANSWER,
            reply_markup=answer_keyboard,
        )

    question_notes = eval(db.get(update.message.chat.id))
    answer_notes = '\n'.join(f'{key}: {value}' for key, value in question_notes.items() if key != 'Вопрос')
    user_answer = update.message.text.lower().strip(' .,:"').replace('ё', 'е')
    correct_answer = question_notes['Ответ'].lower().strip(' .,:"').replace('ё', 'е')
    step = Step.QUESTION
    reply_markup = new_question_keyboard

    if user_answer == correct_answer:
        db.delete(update.message.chat.id)
        answer = f'Урааа! Совершенной верно 👌\n' \
                 f'➕1️⃣ балл\n' \
                 f'Вот что у меня есть по вопросу 👇\n\n' + answer_notes

    elif update.message.text == 'Сдаться':
        db.delete(update.message.chat.id)
        return handle_surrender(update, context, answer_notes)

    else:
        step = Step.ANSWER
        reply_markup = answer_keyboard
        answer = 'Ответ неверный 😔\nПодумай ещё 🤔'

    update.message.reply_text(answer, reply_markup=reply_markup)

    return step


def start(update: Update, context: CallbackContext) -> Step:
    update.message.reply_text(
        f'{update.effective_user.full_name}, будем знакомы - я Бот Ботыч 😍 \nДавай сыграем в викторину?!',
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

    new_question_keyboard = ReplyKeyboardMarkup(
        [['Новый вопрос'],
         ['Мой счёт']]
    )

    answer_keyboard = ReplyKeyboardMarkup(
        [['Сдаться'],
         ['Мой счёт']]
    )

    while True:
        try:
            updater = Updater(tg_token)
            dispatcher = updater.dispatcher

            conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', start)],
                states={
                    Step.QUESTION: [MessageHandler(Filters.regex('Новый вопрос|Мой счёт'), handle_new_question)],
                    Step.ANSWER: [MessageHandler(Filters.text, handle_answer)],
                },
                fallbacks=[CommandHandler('cancel', cancel)],
            )

            dispatcher.add_error_handler(send_err)
            dispatcher.add_handler(conv_handler)

            db = redis_db.connect(
                host=db_host,
                port=db_port,
                password=db_password,
            )

            updater.start_polling()
            updater.idle()

        except Exception as error:
            logger.exception(error)
            time.sleep(60)

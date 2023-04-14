import json
import logging
import random
import time

from environs import Env
from pathlib import Path
from telegram import Bot, ReplyKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from bot_logger import BotLogsHandler

logger = logging.getLogger(__file__)


def get_questions() -> dict[str:dict[str:str]]:
    quizzes_path = Path('quiz-questions/quizzes_parser')
    random_quizzes_file_path = random.choice([*quizzes_path.iterdir()])
    questions = json.loads(random_quizzes_file_path.read_text(encoding='UTF-8'))

    return questions

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        f'{update.effective_user.full_name}, будем знакомы - я Бот Ботыч 😍 \nДавай сыграем в викторину?!',
        reply_markup=reply_markup,
    )


def send_echo_msg(update: Update, context: CallbackContext) -> None:
    if update.message.text == 'Новый вопрос':
        questions = get_questions()
        random_num = random.randrange(1, len(questions) + 1)
        question = questions[str(random_num)]['Вопрос']

        update.message.reply_text(question, reply_markup=reply_markup)

    elif update.message.text == 'Сдаться':
        update.message.reply_text('Тест - Сдаться', reply_markup=reply_markup)

    elif update.message.text == 'Мой счёт':
        update.message.reply_text('Тест - Мой счёт', reply_markup=reply_markup)

    else:
        update.message.reply_text('Я тебя не понял 😔 \nНажми на нужную на кнопку 👇', reply_markup=reply_markup)


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

    bot = Bot(tg_token)
    tg_bot_name = f'@{bot.get_me().username}'
    custom_keyboard = [['Новый вопрос', 'Сдаться'],
                       ['Мой счёт']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard)

    if not admin_tg_token:
        admin_tg_token = tg_token

    logger.addHandler(BotLogsHandler(
        bot_name=tg_bot_name,
        admin_tg_token=admin_tg_token,
        admin_tg_chat_id=admin_tg_chat_id,
    ))



    logger.info('Start Telegram bot.')

    while True:
        try:
            updater = Updater(tg_token)

            dispatcher = updater.dispatcher
            dispatcher.add_error_handler(send_err)
            dispatcher.add_handler(CommandHandler('start', start))
            dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, send_echo_msg))

            updater.start_polling()
            updater.idle()
        except Exception as error:
            logger.exception(error)
            time.sleep(60)

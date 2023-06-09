import json
import logging
import random
import time

from textwrap import dedent

import redis
import vk_api as vk

from environs import Env
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import Event as VkEvent, VkEventType, VkLongPoll
from vk_api.vk_api import VkApiMethod

import quizzes_parser

from bot_logger import BotLogsHandler

LOGGER = logging.getLogger(__name__)

NEW_QUESTION_KEYBOARD = VkKeyboard(one_time=True)
NEW_QUESTION_KEYBOARD.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)
NEW_QUESTION_KEYBOARD.add_button('Новый вопрос', color=VkKeyboardColor.POSITIVE)

ANSWER_KEYBOARD = VkKeyboard(one_time=True)
ANSWER_KEYBOARD.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)
ANSWER_KEYBOARD.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)


def get_answer_notes(user_id: int, db: redis.StrictRedis) -> (str, str):
    question_notes = json.loads(db.get(user_id))
    correct_answer = question_notes['Ответ'].lower().strip(' .,:!\'"').replace('ё', 'е')
    answer_notes = '\n'.join(f'{key}: {value}' for key, value in question_notes.items() if key != 'Вопрос')

    return answer_notes, correct_answer


def handle_answer(event: VkEvent, vk_api: VkApiMethod, db: redis.StrictRedis) -> None:
    keyboard = ANSWER_KEYBOARD.get_keyboard()
    answer_notes, correct_answer = get_answer_notes(event.user_id, db)
    user_answer = event.text.lower().strip(' .,:"').replace('ё', 'е')

    if user_answer == correct_answer:
        db.delete(event.user_id)
        keyboard = NEW_QUESTION_KEYBOARD.get_keyboard()
        answer = dedent(f'''\
            Урааа! Совершенной верно 👌
            ➕1️⃣ балл
            Вот что у меня есть по вопросу 👇
            
        ''') + answer_notes

    else:
        answer = 'Ответ неверный 😔\nПодумай ещё 🤔'

    vk_api.messages.send(
        user_id=event.user_id,
        message=dedent(answer),
        keyboard=keyboard,
        random_id=random.randint(1, 1000),
    )


def handle_fallback(event: VkEvent, vk_api: VkApiMethod) -> None:
    vk_api.messages.send(
        user_id=event.user_id,
        message='Я тебя не понял...\nНажми на кнопку 👇',
        keyboard=NEW_QUESTION_KEYBOARD.get_keyboard(),
        random_id=random.randint(1, 1000),
    )


def handle_my_score(event: VkEvent, vk_api: VkApiMethod, keyboard: VkKeyboard) -> None:
    vk_api.messages.send(
        user_id=event.user_id,
        message='Тест - Мой Счёт',
        keyboard=keyboard,
        random_id=random.randint(1, 1000),
    )


def handle_new_question(event: VkEvent, vk_api: VkApiMethod, db: redis.StrictRedis) -> None:
    question_notes = quizzes_parser.get_random_question_notes()

    vk_api.messages.send(
        user_id=event.user_id,
        message=question_notes['Вопрос'],
        keyboard=ANSWER_KEYBOARD.get_keyboard(),
        random_id=random.randint(1, 1000),
    )

    db.set(event.user_id, json.dumps(question_notes))


def handle_surrender(event: VkEvent, vk_api: VkApiMethod, db: redis.StrictRedis) -> None:
    answer_notes, _ = get_answer_notes(event.user_id, db)

    answer = dedent('''\
        Бывает...
        Вот что у меня есть по вопросу 👇
        
    ''') + answer_notes

    vk_api.messages.send(
        user_id=event.user_id,
        message=answer,
        random_id=random.randint(1, 1000),
    )

    vk_api.messages.send(
        user_id=event.user_id,
        message='Лови новый вопрос 👇',
        random_id=random.randint(1, 1000),
    )

    return handle_new_question(event=event, vk_api=vk_api, db=db)


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')
    LOGGER.setLevel(logging.DEBUG)

    env = Env()
    env.read_env()
    vk_token = env.str('VK_BOT_TOKEN')
    vk_bot_name = env.str('VK_BOT_NAME')
    admin_tg_token = env.str('TELEGRAM_ADMIN_BOT_TOKEN')
    admin_tg_chat_id = env.str('TELEGRAM_ADMIN_CHAT_ID')
    db_host = env.str('REDIS_HOST')
    db_port = env.int('REDIS_PORT')
    db_password = env.str('REDIS_PASSWORD')

    LOGGER.addHandler(BotLogsHandler(
        bot_name=vk_bot_name,
        admin_tg_token=admin_tg_token,
        admin_tg_chat_id=admin_tg_chat_id,
    ))

    LOGGER.info('Start VK bot.')

    while True:
        try:
            vk_session = vk.VkApi(token=vk_token)
            vk_api = vk_session.get_api()
            longpoll = VkLongPoll(vk_session)

            db = redis.StrictRedis(
                host=db_host,
                port=db_port,
                password=db_password,
                charset='utf-8',
                decode_responses=True,
            )

            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    if event.text == 'Новый вопрос':
                        handle_new_question(event=event, vk_api=vk_api, db=db)

                    elif event.text == 'Сдаться':
                        handle_surrender(event=event, vk_api=vk_api, db=db)

                    elif event.text == 'Мой счёт':
                        if db.get(event.user_id):
                            keyboard = ANSWER_KEYBOARD.get_keyboard()

                        else:
                            keyboard = NEW_QUESTION_KEYBOARD.get_keyboard()

                        handle_my_score(event=event, vk_api=vk_api, keyboard=keyboard)

                    else:
                        if db.get(event.user_id):
                            handle_answer(event=event, vk_api=vk_api, db=db)

                        else:
                            handle_fallback(event=event, vk_api=vk_api)

        except Exception as error:
            LOGGER.exception(error)
            time.sleep(60)


if __name__ == '__main__':
    main()

import logging
import vk_api as vk
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import random

from config import VK_TOKEN, QUIZ_FOLDER
from quiz import normalize_answer, get_questions
from db import connect_db


logger = logging.getLogger(__name__)


def send_message(vk_api, user, keyboard, message):
    vk_api.messages.send(
        user_id=user,
        message=message,
        random_id=get_random_id(),
        keyboard=keyboard.get_keyboard()
    )


def create_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('Мой счет', color=VkKeyboardColor.PRIMARY)
    return keyboard


def handle_start(vk_api, user, keyboard):
    welcome_msg = 'Приветствуем в нашей викторине! Нажми кнопку "Новый вопрос"'
    send_message(vk_api, user, keyboard, welcome_msg)


def handle_new_question_request(vk_api, user, keyboard):
    question, answer = random.choice(list(questions.items()))
    redis_db.hmset(user, {'question': question, 'answer': answer})
    send_message(vk_api, user, keyboard, question)


def handle_give_up(vk_api, user, keyboard):
    answer = redis_db.hget(user, 'answer')
    message = f'Правильный ответ:\n{answer}'
    send_message(vk_api, user, keyboard, message)
    handle_new_question_request(vk_api, user, keyboard)


def handle_score(vk_api, user, keyboard):
    score = redis_db.hget(user, 'score') or 0
    message = f'Ваш счет: {score}'
    send_message(vk_api, user, keyboard, message)


def handle_solution_attempt(vk_api, user, keyboard, text):
    correct_answer = redis_db.hget(user, 'answer')

    if correct_answer:
        user_answer = normalize_answer(text)
        normalized_correct_answer = normalize_answer(correct_answer)

        if user_answer == normalized_correct_answer:
            score = redis_db.hget(user, 'score') or 0
            score = int(score) + 1
            send_message(vk_api, user, keyboard, 'Правильный ответ!')
            redis_db.hmset(user, {'score': score})
            handle_new_question_request(vk_api, user, keyboard)
        else:
            send_message(vk_api, user, keyboard, 'Неверно! Попробуйте еще раз')

    else:
        send_message(vk_api, user, keyboard, 'Нажмите "Новый вопрос"')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    redis_db = connect_db()
    questions = get_questions(QUIZ_FOLDER)

    vk_session = vk.VkApi(token=VK_TOKEN)
    vk_api = vk_session.get_api()

    longpoll = VkLongPoll(vk_session)
    keyboard = create_keyboard()

    logger.info('VK Bot works...!')

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user = event.user_id
            if event.text == 'start':
                handle_start(vk_api, user, keyboard)
            elif event.text == 'Новый вопрос':
                handle_new_question_request(vk_api, user, keyboard)
            elif event.text == 'Сдаться':
                handle_give_up(vk_api, user, keyboard)
            elif event.text == 'Мой счет':
                handle_score(vk_api, user, keyboard)
            else:
                handle_solution_attempt(vk_api, user, keyboard, event.text)
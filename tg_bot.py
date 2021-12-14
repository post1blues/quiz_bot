from telegram import ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler
import telegram
import logging
import random

from config import QUESTIONS, TG_TOKEN
from quiz import normalize_answer
from db import redis_db


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def start(bot, update):
    welcome_msg = 'Приветствуем в нашей викторине! Нажми кнопку "Новый вопрос"'
    update.message.reply_text(welcome_msg, reply_markup=REPLY_MARKUP)
    return NEW_QUESTION


def handle_new_question_request(bot, update, user_data):
    user = f'{update.effective_user.id}'
    question = random.choice(list(QUESTIONS.keys()))
    redis_db.hmset(user, {'question': question})
    update.message.reply_text(question, reply_markup=REPLY_MARKUP)
    return ANSWER


def handle_solution_attempt(bot, update, user_data):
    user = f'{update.effective_user.id}'

    if update.message.text == 'Мой счет':
        handle_score(bot, update, user_data)
        return ANSWER

    question = redis_db.hget(user, 'question')
    correct_answer = normalize_answer(QUESTIONS[question])
    user_answer = normalize_answer(update.message.text)

    if user_answer == correct_answer:
        score = redis_db.hget(user, 'score') or 0
        score = int(score) + 1
        redis_db.hmset(user, {'question': score})

        update.message.reply_text(
            'Поздравляю! Для следующего вопроса нажми «Новый вопрос»',
            reply_markup=REPLY_MARKUP
        )
        return NEW_QUESTION

    update.message.reply_text(
        'Неправильно… Попробуешь ещё раз?',
        reply_markup=REPLY_MARKUP
    )
    return ANSWER


def handle_give_up(bot, update, user_data):
    user = f'{update.effective_user.id}'
    question = redis_db.hget(user, 'question')
    correct_answer = QUESTIONS.get(question)
    message = f'Правильный ответ:\n{correct_answer}'

    update.message.reply_text(
        message,
        reply_markup=REPLY_MARKUP
    )
    return NEW_QUESTION


def handle_score(bot, update, user_data):
    user = f'{update.effective_user.id}'
    score = redis_db.hget(user, 'score') or 0
    update.message.reply_text(
        f'Твой счет: {score}'
    )


def cancel(bot, update, user_data):
    update.message.reply_text('Будем вас ждать!', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def error(bot, update, error):
    logger.warning(f'Update {update} caused error {error}')


def main():
    updater = Updater(TG_TOKEN)

    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            RegexHandler('^(Новый вопрос)$', handle_new_question_request, pass_user_data=True)
        ],
        states={
                NEW_QUESTION: [
                    RegexHandler(
                        '^(Новый вопрос)$', handle_new_question_request, pass_user_data=True
                    ),
                ],
                ANSWER: [
                    RegexHandler(
                        '^(Сдаться)$', handle_give_up, pass_user_data=True
                    ),
                    MessageHandler(
                        Filters.text, handle_solution_attempt, pass_user_data=True
                    )
                ],
                GIVE_UP: [
                    RegexHandler(
                        '^(Сдаться)$', handle_give_up, pass_user_data=True
                    ),
                ]

            },
        fallbacks=[
            CommandHandler('finish', cancel, pass_user_data=True),
        ]
    )

    dp.add_handler(conv_handler)
    dp.add_error_handler(error)

    logger.info('TG Bot works...!')
    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    REPLY_MARKUP = telegram.ReplyKeyboardMarkup([['Новый вопрос', 'Сдаться'], ['Мой счет']])
    NEW_QUESTION, ANSWER, GIVE_UP = range(3)
    main()
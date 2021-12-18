from telegram import ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler
import telegram
import logging
import random
from functools import partial

from config import TG_TOKEN, QUIZ_FOLDER
from quiz import normalize_answer, get_questions
from db import connect_db


logger = logging.getLogger(__name__)

REPLY_MARKUP = telegram.ReplyKeyboardMarkup([['Новый вопрос', 'Сдаться'], ['Мой счет']])
NEW_QUESTION, ANSWER, GIVE_UP = range(3)


def start(bot, update):
    welcome_msg = 'Приветствуем в нашей викторине! Нажми кнопку "Новый вопрос"'
    update.message.reply_text(welcome_msg, reply_markup=REPLY_MARKUP)
    return NEW_QUESTION


def handle_new_question_request(bot, update, db, questions):
    user = update.effective_user.id
    question, answer = random.choice(list(questions.items()))
    db.hmset(user, {'question': question, 'answer': answer})
    update.message.reply_text(question, reply_markup=REPLY_MARKUP)
    return ANSWER


def handle_solution_attempt(bot, update, db):
    user = update.effective_user.id

    if update.message.text == 'Мой счет':
        handle_score(bot, update, db)
        return ANSWER

    correct_answer = db.hget(user, 'answer')
    normalized_correct_answer = normalize_answer(correct_answer)
    user_answer = normalize_answer(update.message.text)

    if user_answer == normalized_correct_answer:
        score = db.hget(user, 'score') or 0
        score = int(score) + 1
        db.hmset(user, {'question': score})

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


def handle_give_up(bot, update, db):
    user = update.effective_user.id
    correct_answer = db.hget(user, 'answer')
    message = f'Правильный ответ:\n{correct_answer}'

    update.message.reply_text(
        message,
        reply_markup=REPLY_MARKUP
    )
    return NEW_QUESTION


def handle_score(bot, update, db):
    user = update.effective_user.id
    score = db.hget(user, 'score') or 0
    update.message.reply_text(
        f'Твой счет: {score}',
        reply_markup=REPLY_MARKUP
    )


def cancel(bot, update):
    update.message.reply_text('Будем вас ждать!', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def error(bot, update, error):
    logger.warning(f'Update {update} caused error {error}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parsed_questions = get_questions(QUIZ_FOLDER)
    redis_db = connect_db()

    updater = Updater(TG_TOKEN)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            RegexHandler(
                '^(Новый вопрос)$',
                partial(handle_new_question_request, db=redis_db, questions=parsed_questions))
        ],
        states={
            NEW_QUESTION: [
                RegexHandler(
                    '^(Новый вопрос)$',  partial(handle_new_question_request, db=redis_db, questions=parsed_questions)
                ),
            ],
            ANSWER: [
                RegexHandler(
                    '^(Сдаться)$', partial(handle_give_up, db=redis_db)
                ),
                MessageHandler(
                    Filters.text, partial(handle_solution_attempt, db=redis_db)
                )
            ],
            GIVE_UP: [
                RegexHandler(
                    '^(Сдаться)$', partial(handle_new_question_request, db=redis_db)
                ),
            ]

        },
        fallbacks=[
            CommandHandler('finish', cancel),
        ]
    )

    dp.add_handler(conv_handler)
    dp.add_error_handler(error)

    logger.info('TG Bot works...!')
    updater.start_polling()

    updater.idle()
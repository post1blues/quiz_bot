import logging
from pathlib import Path
from environs import Env


logger = logging.getLogger(__name__)


def clean_text(text):
    return ' '.join(text.strip().split('\n')[1:])


def normalize_answer(text):
    return text.split('.')[0].lower()


def get_quiz_files(folder):
    folder_path = Path(f'./{folder}')
    quiz_files = []
    for file in folder_path.iterdir():
        if file.is_file() and file.suffix == '.txt':
            quiz_files.append(file.absolute())
    return quiz_files


def read_questions_file(filename):
    questions = dict()
    with open(filename, 'r', encoding='KOI8-R') as file:
        questions_content = file.read().split('\n\n')
        question = ''
        answer = ''
        for text in questions_content:
            text = text.strip()
            if text.startswith('Вопрос'):
                question = clean_text(text)
            if text.startswith('Ответ'):
                answer = clean_text(text)
                questions[question] = answer
    return questions


def get_questions(folder):
    logger.info('Read all files with questions')
    files = get_quiz_files(folder)
    questions = dict()
    for file in files:
        file_questions = read_questions_file(file)
        questions.update(file_questions)
    logger.info('Finished reading files with questions')
    return questions


import argparse
import json
import random
import re

from pathlib import Path


PARSER_FOLDER_PATH = Path('quizzes_parser')


def get_random_question_notes() -> dict[str:str]:
    random_quizzes_file_path = random.choice([*PARSER_FOLDER_PATH.iterdir()])
    questions = json.loads(random_quizzes_file_path.read_text(encoding='UTF-8'))
    del questions['0']
    random_question_notes = random.choice([*questions.values()])

    return random_question_notes


def parse_questions(text: str) -> dict[int:dict[str:str]]:
    questions = {}

    for num, question in enumerate(re.split('\nВопрос \d+', text), start=0):
        if question[0] == ':':
            question = 'Вопрос' + question

        questions[num] = parse_question_notes(question.strip(), num)

    return questions


def parse_question_notes(question: str, num: int) -> dict[str:str]:
    question_notes = {}
    error_str_limit = 1000
    question_num_index = 0
    question_notes_index = 1


    for notes in question.strip().split('\n\n'):
        notes = notes.split(':\n', maxsplit=1)

        if len(notes) > 1 and '.jpg' not in notes[question_notes_index]:
            question_notes[notes[question_num_index]] = notes[question_notes_index].strip()

        else:
            if not quizzes_errors.get(quiz_file.name):
                quizzes_errors[quiz_file.name] = {}

            question_notes = {f'ERROR': question[:error_str_limit]}
            quizzes_errors[quiz_file.name][f'ERROR in question №{num}'] = question_notes['ERROR']

    return question_notes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Парсинг вопросов для викторины из json файлов')
    parser.add_argument('-p', '--path', type=str, default='quizzes', help='Введите путь к директории с json файлами, по умолчанию "quizzes"')
    args = parser.parse_args()

    quizzes_folder_path = Path(args.path)
    parser_errors_folder_path = Path('quizzes_parser_errors')
    PARSER_FOLDER_PATH.mkdir(exist_ok=True)
    parser_errors_folder_path.mkdir(exist_ok=True)

    quizzes = {}
    quizzes_errors = {}

    for quiz_file in quizzes_folder_path.iterdir():
        if quiz_file.is_file():
            quizzes[quiz_file.name] = parse_questions(quiz_file.read_text(encoding='KOI8-R'))

    for file_name, questions in quizzes.items():
        file_path = PARSER_FOLDER_PATH / file_name
        with open(file_path.with_suffix('.json'), 'w', encoding='UTF-8') as file:
            json.dump(questions, file, ensure_ascii=False, indent=4)

    if quizzes_errors:
        with open(parser_errors_folder_path / 'errors.json', 'w', encoding='UTF-8') as file:
            json.dump(quizzes_errors, file, ensure_ascii=False, indent=4)

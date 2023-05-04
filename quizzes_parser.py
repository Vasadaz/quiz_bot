import json
import random
import re
import traceback

from pathlib import Path


def get_question_notes() -> dict[str:str]:
    quizzes_path = Path('quizzes/quizzes_parser')
    random_quizzes_file_path = random.choice([*quizzes_path.iterdir()])
    questions = json.loads(random_quizzes_file_path.read_text(encoding='UTF-8'))
    random_num = random.randrange(1, len(questions))

    while not questions[str(random_num)].get('Вопрос', ''):
        random_num = random.randrange(1, len(questions))

    return questions[str(random_num)]


def parse_questions(text: str) -> list[str]:
    questions = []

    for note in re.split('\nВопрос \d+', text):
        if note[0] == ':':
            questions.append('Вопрос' + note.strip())
        else:
            questions.append(note.strip())

    return sterilize_questions(questions)


def parse_question_notes(question: str, num: int) -> dict[str:str]:
    question_notes = {}
    error_str_limit = 1000

    for notes in question.strip().split('\n\n'):
        if notes:
            try:
                notes = notes.split(':\n', maxsplit=1)
                if '.jpg' not in notes[1]:
                    question_notes[notes[0]] = notes[1].strip()
                else:
                    raise ValueError

            except IndexError:
                question_notes = {
                    f'ERROR': {
                        'question': question[:error_str_limit],
                        'crash_str': notes[0][:error_str_limit],
                        'traceback': traceback.format_exc(),
                    }
                }

                if not quizzes_errors.get(quiz_file.name):
                     quizzes_errors[quiz_file.name] = {}

                quizzes_errors[quiz_file.name][f'ERROR in question №{num}'] = question_notes['ERROR']

                return question_notes

            except ValueError:
                question_notes = {
                    f'ERROR': {
                        'question': question[:error_str_limit],
                        'crash_str': notes[1][:error_str_limit],
                        'traceback': traceback.format_exc(),
                    }
                }

                if not quizzes_errors.get(quiz_file.name):
                     quizzes_errors[quiz_file.name] = {}

                quizzes_errors[quiz_file.name][f'ERROR in question №{num}'] = question_notes['ERROR']

                return question_notes

    return question_notes


def sterilize_questions(questions: list) -> dict[int:dict[str:str]]:
    sterilized_questions = {}
    for num, question in enumerate(questions, start=0):
        sterilized_questions[num] = parse_question_notes(question, num)
    return sterilized_questions


if __name__ == '__main__':
    quizzes_folder_path = Path('quizzes')
    parser_folder_path = quizzes_folder_path / 'quizzes_parser'
    parser_folder_path.mkdir(exist_ok=True)

    quizzes = {}
    quizzes_errors = {}

    for quiz_file in quizzes_folder_path.iterdir():
        if quiz_file.is_file():
            quizzes[quiz_file.name] = parse_questions(quiz_file.read_text(encoding='KOI8-R'))

    for file_name, questions in quizzes.items():
        file_path = parser_folder_path / file_name
        with open(file_path.with_suffix('.json'), 'w', encoding='UTF-8') as file:
            json.dump(questions, file, ensure_ascii=False, indent=4)

    if quizzes_errors:
        parser_errors_folder_path = quizzes_folder_path / 'quizzes_parser_errors'
        parser_errors_folder_path.mkdir(exist_ok=True)

        with open(parser_errors_folder_path / 'errors.json', 'w', encoding='UTF-8') as file:
            json.dump(quizzes_errors, file, ensure_ascii=False, indent=4)

import json
import re

from pathlib import Path


def parse_questions(text: str) -> list[str]:
    questions = []

    for note in re.split('\nВопрос \d+', text):
        if note[0] == ':':
            questions.append('Вопрос' + note.strip())
        else:
            questions.append(note.strip())

    return sterilize_questions(questions)


def parse_question_notes(question: str) -> dict[str:str]:
    question_notes = {}

    for notes in question.strip().split('\n\n'):
        if notes:
            try:
                notes = notes.split(':\n', maxsplit=1)
                question_notes[notes[0]] = notes[1].strip()

            except IndexError as err:
                print(f'ERROR: {quiz_file} {err}')
                question_notes = {f'ERROR {err}': (question, notes)}
                quiz_parser_errors[quiz_file.name] = question_notes

                return question_notes

    return question_notes


def sterilize_questions(questions: list) -> dict[int:dict[str:str]]:
    sterilized_questions = {}
    for num, question in enumerate(questions, start=0):
        sterilized_questions[num] = parse_question_notes(question)
    return sterilized_questions


if __name__ == '__main__':
    quiz_folder_path = Path('quiz-questions')
    parser_folder_path = quiz_folder_path / 'quizzes_parser'
    parser_folder_path.mkdir(exist_ok=True)

    quizzes = {}
    quiz_parser_errors = {}

    for quiz_file in quiz_folder_path.iterdir():
        if quiz_file.is_file():
            quizzes[quiz_file] = parse_questions(quiz_file.read_text(encoding='KOI8-R'))

    with open(parser_folder_path / 'quizzes.json', 'w', encoding='UTF-8') as file:
        json.dump(quiz_parser_errors, file, ensure_ascii=False, indent=4)

    with open(parser_folder_path / 'errors.json', 'w', encoding='UTF-8') as file:
        json.dump(quiz_parser_errors, file, ensure_ascii=False, indent=4)
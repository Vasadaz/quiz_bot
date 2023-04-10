import re
from pprint import pprint
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

    for notes in question.split('\n\n'):
        notes = notes.split(':\n', maxsplit=1)
        question_notes[notes[0]] = notes[1].strip()

    return question_notes


def sterilize_questions(questions: list) -> dict[int:dict[str:str]]:
    sterilized_questions = {}
    for num, question in enumerate(questions, start=0):
        sterilized_questions[num] = parse_question_notes(question)
    return sterilized_questions


if __name__ == '__main__':
    quiz_folder_path = Path('./quiz-questions/')

    quizzes = {}

    for quiz_file in quiz_folder_path.iterdir():

        quizzes[quiz_file] = parse_questions(quiz_file.read_text(encoding='KOI8-R'))

    pprint(quizzes)

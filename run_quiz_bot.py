from pathlib import Path

quiz_folder_path = Path('./quiz-questions/')

for quiz_file in quiz_folder_path.iterdir():
    with open(quiz_file, 'r', encoding='KOI8-R') as file:
        print(file.read())

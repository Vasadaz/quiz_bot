# Боты для провидения викторин 

Проект позволяет запустить ботов Telegram и VK для проведения викторин.
Боты умеют анализировать ответ пользователя и начислять балы за правильные ответы.
Также реализован парсинг вопросов для викторины из `txt` файлов. 

Примеры:

   - [Бот Telegram](https://t.me/DevmanLessonsBot)

     ![tg.gif](docs/Ftg.gif)


   - [Бот VK](https://vk.com/club219388423)

     ![vk.gif](docs/vk.gif)


## Как установить


1. Клонировать репозиторий:
    ```shell
    git clone https://github.com/Vasdaz/quiz_bot.git
    ```


2. Установить зависимости:
    ```shell
    pip install -r requirements.txt
    ```


3. [Создать двух Telegram ботов](https://telegram.me/BotFather).
   - Первый бот будет основной для работы с пользователями;
   - Второй бот нужен для отправки сообщений об ошибках в основных ботах для Telegram и VK.
   Его необходимо сразу активировать, т.е. инициализировать с ним диалог нажав на кнопку `СТАРТ(/start)`,
   иначе он не сможет отправлять вам сообщения.


4. 1. [Создать группу VK](https://vk.com/faq18025);
   2. [Получить токен VK бот для сообщества](https://vk.com/@articles_vk-token-groups).


5. [Создать БД Redis](https://developer.redis.com/create/redis-stack).


6. Создать файл `.env` с данными:
    ```dotenv
    REDIS_HOST=redis-564525.a12.us-east-1-2.ec2.cloud.redislabs.com # Хост для пдключения к БД Redis 
    REDIS_PASSWORD=NA7...ztX # Пароль root для аутентификации в БД Redis
    REDIS_PORT=564525 # Порт для пдключения к БД Redis 
    TELEGRAM_ADMIN_BOT_TOKEN=5934478120:AAF...4X8 # Токен бота Telegram для отправки сообщений об ошибках.
    TELEGRAM_ADMIN_CHAT_ID=123456789 # Ваш id Telegram, сюда будут отправлятся сообщения об ошибках.
    TELEGRAM_BOT_TOKEN=581247650:AAH...H7A # Токен основного бота Telegram.
    VK_BOT_NAME="Бот VK https://vk.com/club219388423" # Имя бота VK для сообщениий TELEGRAM_ADMIN_BOT. 
    VK_BOT_TOKEN=vk1.a.tjC...NQ-g # Токен бота VK.
    ```
   
7. Подготовить вопросы для ботов:
   1. Создать файлы с вопросами по [примеру](docs/example_quize.txt);
   2. Положить все файлы в директорию `quizzes`;
   3. Запустить скрипт для анализа файлов:
      ```shell
      python3 quizzes_parser.py
      ```
      Результат запуска скрипта:
      - `quizzes/quizzes_parser` - это директория создастся для хранения в ней JSON файлов викторин;
      - `quizzes/quizzes_parser_errors` - это директория создастся для хранения в ней JSON файла с ошибками при 
      парсинге вопросов, при этом такие вопросы не будут отправляться пользователю.


8. Запуск ботов:
   - Telegram:
     ```shell
     python3 run_tg_bot.py
     ```
        
   - VK:
     ```shell
     python3 run_vk_bot.py
     ```
    
### Цель проекта

Код написан в образовательных целях на онлайн-курсе для веб-разработчиков [dvmn.org](https://dvmn.org/).

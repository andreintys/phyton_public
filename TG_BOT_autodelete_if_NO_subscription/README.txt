Приветствую! В этом файле я опишу схему работы бота.


Команды:
    - /start = Приветственное сообщение от бота. Уровень доступа: любой
        Человеку из ADMIN_IDS откроется доступ к админ панели (управления доступом).
    - /cancel = Отмена ввода/отправки данных. Уровень доступа: любой.
    - /help = Отправка сообщения с описанием работы.
        Уровень доступа: любой.
    - /clear = Отправка сообщения с просьбой подтверждения удаления всех чатов из списка.
        Уровень доступа: любой/whitelist.
    - /status = Отправка сообщения с основным чатом пользователя и каналами для подписки.
        Уровень доступа: любой/whitelist.

    - /get_logs = Получение логов за сегодня файлом.
        Уровень доступа: ADMIN_IDS из конфига.


Как пользоваться:
    1) Добавьте бота в чат.
    2) Добавьте бота в каналы, на которые нужно подписаться.
    3) В чате из шага №1 пропишите команду:
        /kanal @username1 @username2 @username3
    Где @usernameX - username канала, на который нужно подписываться.

    В сумме не более 5 каналов/чатов.


После добавления бота в чат, он начнет получать все сообщения из этого чата.
Одного пользователя он проверяет 1 раз в день на один чат (по настройке в конфиге). Чтобы не нагружать Telegram запросами.
То есть, если человек утром подписался на два чата, но днем добавился третий - с него спросит за третий чат.


Файлы:
    - config.py = Конфиг бота. В нем нужно задать токен от телеграмм бота.
                Также в нем можно добавить ID людей, которые смогут
                получать логи в чате с ботом и менять доступность.
    - messages.py = Текста сообщений от бота. В некоторых этих сообщениях можно применять разметку html.
                То есть, <b>слово</b> - жирный шрифт; <i>слово</i> - курсив.
                Переносить строчку можно в тройных кавычках """слово""", или с помощью символа \n
                в обычных кавычках. Например: 1\n2\n3


Установка:
    - Запускаемый файл: main.py
    - Файл с необходимыми библиотеками: requirements.txt

    - Установка библиотек на Linux: "pip install -r requirements.txt" (возможно pip3)
    - Запуск на Linux: "python3 main.py"


made by https://kwork.ru/user/juicefw
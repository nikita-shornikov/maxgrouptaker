# MAX Group Taker — добавление в группу по имени (веб)

Скрипт для **добавления пользователей в группу мессенджера MAX по имени** через веб-интерфейс [web.max.ru](https://web.max.ru) с помощью Playwright. API не требуется.

## Что делает скрипт

1. Открывает веб-версию MAX в браузере.
2. Вы авторизуетесь (QR-код или пароль).
3. Переходит в указанную группу.
4. Открывает меню добавления участников, вводит **имя** в поле «Найти по имени».
5. Находит **все** результаты с этим именем и добавляет **всех** найденных в группу.
6. Подтверждает добавление.

## Требования

- **Python 3.10+**
- **Playwright** и браузер (например Chromium)

## Установка

```bash
# Клонируйте или перейдите в каталог проекта
cd maxgrouptaker

# Установите зависимости
pip install -r requirements.txt

# Установите браузеры Playwright (один раз)
playwright install chromium
```

Установка пакета в режиме разработки (опционально):

```bash
pip install -e .
```

## Конфигурация

1. Создайте конфиг из примера:

   ```bash
   copy config.example.yaml config.yaml
   ```

2. Файл `config.yaml` нужен для **селекторов** веб-интерфейса. Если интерфейс web.max.ru изменится, можно подправить селекторы в `web_automation.selectors`. По умолчанию указаны селекторы под текущий интерфейс MAX.

3. Файл `config.yaml` не коммитится в git (указан в `.gitignore`).

## Использование

**Запуск (интерактивный ввод ID группы и имени):**

```bash
python script2_web_add_to_group.py
```

**С параметрами:**

```bash
python script2_web_add_to_group.py --chat-id -71285852438766 --name "Иван Петров"
```

**Параметры:**

| Параметр     | Описание |
|-------------|----------|
| `--chat-id` | ID группы-приёмника (из URL: `https://web.max.ru/-71285852438766` → `-71285852438766`) |
| `--name`    | Имя для поиска; добавляются **все** пользователи с этим именем |
| `--config`  | Путь к `config.yaml` (по умолчанию: `config.yaml`) |
| `--headless`| Запуск браузера без окна |
| `--browser` | Браузер: `chromium`, `firefox`, `webkit` (по умолчанию: `chromium`) |

**Примеры:**

```bash
# Группа и имя в командной строке
python script2_web_add_to_group.py --chat-id -71285852438766 --name "Мария"

# Свой конфиг и headless
python script2_web_add_to_group.py --config my_config.yaml --headless --name "Алексей"
```

## Как узнать ID группы

1. Откройте группу в [web.max.ru](https://web.max.ru).
2. Посмотрите URL: `https://web.max.ru/-71285852438766`.
3. Число после `/` (с минусом) — это ID группы, например: `-71285852438766`.

## Селекторы (config.yaml)

В `config.example.yaml` в блоке `web_automation.selectors` перечислены CSS-селекторы кнопок и полей веб-интерфейса MAX. Если после обновления сайта скрипт перестал находить кнопки или поля — откройте инструменты разработчика (F12), найдите нужный элемент и обновите соответствующий селектор в `config.yaml`.

## Структура проекта

```
maxgrouptaker/
├── script2_web_add_to_group.py   # Точка входа
├── config.example.yaml           # Пример конфига (селекторы и timeout)
├── src/maxgrouptaker/
│   ├── __init__.py
│   └── web_automation.py         # Playwright-автоматизация MAX
├── README.md
├── CONTRIBUTING.md
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

## Лицензия

MIT.

## Ссылки

- [MAX для разработчиков](https://dev.max.ru)
- [Playwright для Python](https://playwright.dev/python/)

# Telegram Educational Bot

Інформаційна система планування та організації навчальної діяльності у вигляді Telegram-бота.

## Архітектура проєкту

```
┌─────────────────────────────────────────────────────────────┐
│                        Telegram API                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Bot (Aiogram 3.x)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Handlers    │  │ Services    │  │ Database Layer      │  │
│  │ - Admin     │  │ - Scheduler │  │ - SQLite            │  │
│  │ - Teacher   │  │ - ICS Parser│  │ - Models            │  │
│  │ - Student   │  │ - SUMDU API │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│  - SUMDU API (Academic data)                                │
│  - ICS Schedule Files                                       │
└─────────────────────────────────────────────────────────────┘
```

### Компоненти проєкту

| Компонент | Призначення | Технологія |
|-----------|-------------|------------|
| Telegram Bot | Основний інтерфейс взаємодії з користувачами | Aiogram 3.x |
| Web Server | Не потрібен ( polling mode ) | - |
| Application Server | Не потрібен | - |
| СУБД | Зберігання даних користувачів, груп, розкладів | SQLite |
| Файлове сховище | Конфігураційні файли, логи | Локальна файлова система |
| Кешування | Кешування API-відповідей | Python cachetools |
| Scheduler | Планування завдань (сповіщення) | APScheduler |

## Функціонал

- 📅 Перегляд розкладу занять
- 🔔 Автоматичні сповіщення
- 👥 Управління групами
- 👨‍💼 Адміністративний модуль

## Технології

- Python 3.11+
- Aiogram 3.x
- SQLite
- APScheduler

---

## Інструкція для розробника

### 1. Необхідне програмне забезпечення

Перед початком роботи переконайтесь, що у вас встановлено:

| ПЗ | Версія | Призначення |
|----|--------|-------------|
| Python | 3.11+ | Основна мова програмування |
| Git | будь-яка | Контроль версій |
| pip | остання | Менеджер пакетів Python |
| SQLiteStudio | 3.x+ | Перегляд бази даних (опціонально) |

#### Перевірка встановлення Python:

```bash
python --version
# Очікуваний вивід: Python 3.11.x
```

### 2. Клонування репозиторію

```bash
# Клонування репозиторію
git clone <repository-url>
cd telegram-edu-bot

# Перевірка структури проєкту
ls -la
```

### 3. Створення віртуального середовища

```bash
# Створення віртуального середовища
python -m venv venv

# Активація віртуального середовища
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Перевірка активації (з'явиться (venv) на початку рядка)
```

### 4. Встановлення залежностей

```bash
# Оновлення pip до останньої версії
pip install --upgrade pip

# Встановлення залежностей
pip install -r requirements.txt
```

### 5. Налаштування конфігурації

```bash
# Копіювання файлу прикладів конфігурації
copy .env.example .env
# Або для Linux/macOS:
cp .env.example .env

# Редагування конфігураційного файлу
nano .env
```

#### Обов'язкові параметри в `.env`:

```env
# Telegram Bot Token (отримайте у @BotFather)
BOT_TOKEN=your_bot_token_here

# Режим роботи: development / production
ENVIRONMENT=development

# Шлях до бази даних
DATABASE_PATH=./data/bot.db

# Логування
LOG_LEVEL=INFO

# API SUMDU (якщо потрібно)
SUMDU_API_URL=https://api.sumdu.edu.ua
```

### 6. Створення директорій для даних

```bash
# Створення директорії для даних
mkdir -p data logs

# Структура після створення:
# telegram-edu-bot/
# ├── data/          # База даних
# ├── logs/          # Логи
# ├── venv/          # Віртуальне середовище
# └── ...
```

### 7. Запуск проекту у режимі розробки

```bash
# Перевірка конфігурації
python -c "from config.settings import settings; print('Config loaded successfully')"

# Запуск бота
python main.py
```

Або з детальним логуванням:

```bash
# Запуск з виводом детальних логів
python main.py --log-level DEBUG
```

### 8. Базові команди та операції

#### Команди для роботи з проектом:

```bash
# Активація віртуального середовища
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Запуск
python main.py

# Зупинка (Ctrl+C в терміналі)

# Перевірка статусу
python -c "from main import app; print('Bot initialized')"
```

#### Запуск тестів:

```bash
# Встановлення тестових залежностей
pip install -r requirements-test.txt

# Запуск всіх тестів
pytest tests/ -v

# Запуск з покриттям коду
pytest tests/ --cov=.

# Запуск конкретного тесту
pytest tests/test_models.py -v
```

#### Перевірка коду (линтинг):

```bash
# Встановлення линтера
pip install flake8

# Перевірка коду
flake8 . --max-line-length=100

# Автоматичне виправлення (опціонально)
pip install black
black . --check
```

### 9. Структура проєкту

```
telegram-edu-bot/
├── main.py                    # Точка входу
├── config/
│   ├── __init__.py
│   ├── init.py
│   └── settings.py            # Конфігурація
├── database/
│   ├── __init__.py
│   ├── init.py
│   └── models.py              # Моделі даних
├── handlers/
│   ├── __init__.py
│   ├── admin_commands.py      # Адмін-команди
│   ├── student_commands.py    # Команди студентів
│   ├── teacher_commands.py    # Команди викладачів
│   ├── cabinet.py             # Кабінет користувача
│   ├── communication.py       # Комунікація
│   └── ics_schedule.py        # Робота з ICS
├── services/
│   ├── __init__.py
│   ├── scheduler.py           # Планувальник
│   ├── ics_parser.py          # Парсер розкладів
│   ├── sumdu_api.py           # API університету
│   └── sumdu_cabinet.py       # Кабінет студента
├── utils/
│   ├── __init__.py
│   └── decorators.py          # Декоратори
├── tests/
│   ├── test_models.py
│   └── test_integration.py
├── features/                   # BDD тести (Behave)
├── data/                       # База даних
├── logs/                       # Логи
├── .env                        # Конфігурація
├── requirements.txt            # Залежності
└── README.md                   # Документація
```

### 10. Розробка нових функцій

```bash
# Створення нової гілки
git checkout -b feature/new-feature

# Внесення змін
# ...

# Коміт змін
git add .
git commit -m "feat: додано нову функцію"

# Push до репозиторію
git push origin feature/new-feature
```

### 11. Вирішення проблем

#### Проблема: "ModuleNotFoundError"
```bash
# Перевірка встановлення залежностей
pip list | grep aiogram

# Повторне встановлення
pip install -r requirements.txt
```

#### Проблема: "Token is invalid"
```bash
# Перевірка токена в .env файлі
cat .env | grep BOT_TOKEN

# Оновлення токена
nano .env
```

#### Проблема: База даних заблокована
```bash
# Закриття всіх з'єднань з базою даних
# Перезапуск бота
python main.py
```

### Корисні посилання

- [Документація Aiogram](https://docs.aiogram.dev/)
- [Документація Python](https://docs.python.org/)
- [PyTest Documentation](https://docs.pytest.org/)

---

## Ліцензія

MIT License

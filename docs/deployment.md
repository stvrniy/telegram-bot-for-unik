# Розгортання у виробничому середовищі (Production Deployment)

## 1. Вимоги до апаратного забезпечення

### Мінімальні вимоги

| Параметр | Мінімальні | Рекомендовані |
|----------|------------|---------------|
| CPU | 1 ядро (x86_64/arm64) | 2+ ядра |
| Пам'ять (RAM) | 512 MB | 1 GB |
| Диск | 5 GB HDD/SSD | 10+ GB SSD |
| Мережа | 10 Mbps | 100 Mbps |

### Підтримувані платформи

- Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+)
- Windows Server 2019+
- Docker-контейнери (рекомендовано)

---

## 2. Необхідне програмне забезпечення

### Для Linux (Ubuntu/Debian):

```bash
# Оновлення пакетів
sudo apt update && sudo apt upgrade -y

# Встановлення Python 3.11+
sudo apt install -y python3.11 python3.11-venv python3-pip git

# Встановлення додаткових залежностей
sudo apt install -y libssl-dev libffi-dev build-essential
```

### Для Windows:

1. Завантажити Python 3.11+ з [python.org](https://www.python.org/downloads/)
2. Встановити з опцією "Add Python to PATH"
3. Завантажити та встановити Git

### Для Docker (рекомендовано):

```bash
# Встановлення Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Встановлення Docker Compose
sudo pip install docker-compose
```

---

## 3. Налаштування мережі

### Вимоги до мережі

| Порт | Протокол | Призначення |
|-----|----------|-------------|
| 443 | HTTPS | Telegram Webhook (якщо використовується) |
| 80 | HTTP | Let's Encrypt (сертифікати) |
| 22 | SSH | Адміністрування |

### Налаштування firewall (UFW для Ubuntu):

```bash
# Дозволити SSH
sudo ufw allow ssh

# Дозволити HTTP/HTTPS (якщо є веб-сервер)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Увімкнути firewall
sudo ufw enable
```

### Налаштування Telegram Webhook

Якщо використовуєте webhook замість polling:

```bash
# Відкрити порт для webhook
sudo ufw allow 8443/tcp
```

---

## 4. Конфігурація серверів

### Створення користувача для бота

```bash
# Створення окремого користувача
sudo adduser botuser
sudo usermod -aG sudo botuser

# Перехід до користувача
sudo su - botuser
```

### Створення директорій:

```bash
# Створення структури директорій
sudo mkdir -p /opt/telegram-bot/{data,logs,backups}
sudo chown -R botuser:botuser /opt/telegram-bot
```

### Налаштування systemd service:

```bash
# Створення файлу сервісу
sudo nano /etc/systemd/system/telegram-bot.service
```

```ini
[Unit]
Description=Telegram Educational Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/opt/telegram-bot
Environment=PATH=/opt/telegram-bot/venv/bin
Environment=ENVIRONMENT=production
ExecStart=/opt/telegram-bot/venv/bin/python main.py
Restart=always
RestartSec=10

# Логування
StandardOutput=append:/opt/telegram-bot/logs/bot.log
StandardError=append:/opt/telegram-bot/logs/bot_error.log

# Захист
ProtectSystem=strict
ReadWritePaths=/opt/telegram-bot/data /opt/telegram-bot/logs
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

---

## 5. Налаштування СУБД

### SQLite (використовується за замовчуванням)

База даних SQLite не потребує окремого налаштування сервера.

```bash
# Створення директорії для бази даних
mkdir -p /opt/telegram-bot/data

# Встановлення прав доступу
chmod 700 /opt/telegram-bot/data
```

### Оптимізація SQLite для production:

```bash
# Створення файлу конфігурації SQLite
cat >> /opt/telegram-bot/.sqlite.conf << EOF
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-64000;
PRAGMA temp_store=MEMORY;
PRAGMA mmap_size=268435456;
EOF
```

---

## 6. Розгортання коду

### Метод 1: Клонування з Git

```bash
# Перехід до директорії проекту
cd /opt/telegram-bot

# Клонування репозиторію
git clone <repository-url> .
git checkout <branch-name>

# Створення віртуального середовища
python3 -m venv venv

# Активація та встановлення залежностей
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Створення конфігурації
cp .env.example .env
nano .env
```

### Метод 2: Docker (рекомендовано)

```bash
# Клонування репозиторію
cd /opt/telegram-bot
git clone <repository-url> .

# Збірка та запуск
docker-compose up -d --build
```

---

## 7. Конфігурація production .env

```bash
nano /opt/telegram-bot/.env
```

```env
# Production конфігурація
BOT_TOKEN=your_production_bot_token
ENVIRONMENT=production
DATABASE_PATH=/opt/telegram-bot/data/bot.db
LOG_LEVEL=WARNING
LOG_FILE=/opt/telegram-bot/logs/bot.log

# Безпека
ALLOWED_USERS=123456789,987654321
ADMIN_IDS=123456789

# API налаштування (якщо потрібно)
SUMDU_API_URL=https://api.sumdu.edu.ua
REQUEST_TIMEOUT=30
MAX_RETRIES=3

# Scheduler
SCHEDULER_ENABLED=true
NOTIFICATION_TIME=07:00
```

---

## 8. Перевірка працездатності

### Перевірка статусу сервісу:

```bash
# Перевірка статусу systemd
sudo systemctl status telegram-bot.service

# Перегляд логів
sudo journalctl -u telegram-bot.service -f

# Перегляд останніх записів
tail -f /opt/telegram-bot/logs/bot.log
```

### Тестування бота:

```bash
# Перевірка запуску
curl http://localhost:8080/health  # Якщо є health endpoint

# Перевірка в Telegram
# Відправте команду /start боту
```

### Ознаки успішного запуску:

```log
# В логах повинно бути:
[INFO] Bot started successfully
[INFO] Database connected: /opt/telegram-bot/data/bot.db
[INFO] Scheduler started
[INFO] Polling mode: active
```

### Health check скрипт:

```bash
#!/bin/bash
# health_check.sh

LOG_FILE="/opt/telegram-bot/logs/bot.log"
ERROR_FILE="/opt/telegram-bot/logs/bot_error.log"

# Перевірка запущеного процесу
if ! pgrep -f "python main.py" > /dev/null; then
    echo "ERROR: Bot process not running"
    exit 1
fi

# Перевірка логів на помилки
if tail -n 10 "$ERROR_FILE" | grep -q "ERROR\|CRITICAL"; then
    echo "WARNING: Errors found in log file"
    exit 1
fi

# Перевірка розміру логів
LOG_SIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
if [ "$LOG_SIZE" -gt 104857600 ]; then
    echo "WARNING: Log file too large (>100MB)"
fi

echo "OK: Bot is running"
exit 0
```

---

## 9. Запуск у production

```bash
# Перезавантаження конфігурації systemd
sudo systemctl daemon-reload

# Увімкнення автозапуску
sudo systemctl enable telegram-bot.service

# Запуск сервісу
sudo systemctl start telegram-bot.service

# Перевірка статусу
sudo systemctl status telegram-bot.service
```

### Перевірка після запуску:

```bash
# Перевірка логів
sudo journalctl -u telegram-bot.service -n 50 --no-pager

# Перевірка з'єднання з базою даних
sqlite3 /opt/telegram-bot/data/bot.db "SELECT COUNT(*) FROM users;"
```

---

## 10. Rollback (відкат)

У разі проблем, виконайте:

```bash
# Зупинка сервісу
sudo systemctl stop telegram-bot.service

# Відкат до попередньої версії
cd /opt/telegram-bot
git checkout HEAD~1

# Або відкат до тегу
git checkout v1.0.0

# Перезапуск
sudo systemctl start telegram-bot.service

# Перевірка
sudo systemctl status telegram-bot.service
```

### Швидкий відкат Docker:

```bash
cd /opt/telegram-bot
docker-compose down
docker-compose up -d --rollback
```

# Резервне копіювання та відновлення (Backup & Recovery)

## 1. Стратегія резервного копіювання

### 1.1 Типи резервних копій

| Тип | Опис | Переваги | Недоліки |
|-----|------|----------|----------|
| Повна (Full) | Повна копія всіх даних | Повне відновлення | Великий розмір, довго |
| Інкрементальна (Incremental) | Зміни з останнього будь-якого backup | Малий розмір, швидко | Потребує всіх попередніх |
| Диференціальна (Differential) | Зміни з останнього повного backup | Баланс розміру/швидкості | Середній розмір |

### 1.2 Рекомендована стратегія

```
Щоденно:  Інкрементальні (о 02:00)
Щотижнеly: Повні (неділя о 03:00)
Зберігання: 30 днів локально + 90 днів віддалено
```

---

## 2. Частота створення резервних копій

| Дані | Частота | Зберігання |
|------|---------|------------|
| База даних | Щоденно + перед оновленням | 30 днів |
| Конфігурація | При кожній зміні | 90 днів |
| Логи | Архівування щомісяця | 365 днів |
| Медіа-файли | Щотижнево | 90 днів |

---

## 3. Процедура резервного копіювання

### 3.1 Автоматичне резервне копіювання

```bash
#!/bin/bash
# backup.sh - Скрипт резервного копіювання

set -e

# Конфігурація
BOT_DIR="/opt/telegram-bot"
BACKUP_DIR="${BOT_DIR}/backups"
DATA_DIR="${BOT_DIR}/data"
LOG_DIR="${BOT_DIR}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Створення директорії для резервних копій
mkdir -p "${BACKUP_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 1. Резервне копіювання бази даних
backup_database() {
    log "Starting database backup..."
    
    DB_FILE="${DATA_DIR}/bot.db"
    BACKUP_FILE="${BACKUP_DIR}/bot_db_${TIMESTAMP}.db"
    
    if [ -f "$DB_FILE" ]; then
        # SQLite backup with integrity check
        sqlite3 "$DB_FILE" "PRAGMA integrity_check;"
        cp "$DB_FILE" "$BACKUP_FILE"
        gzip "$BACKUP_FILE"
        
        log "Database backup created: ${BACKUP_FILE}.gz"
        echo "$BACKUP_FILE.gz"
    else
        log "ERROR: Database file not found"
        return 1
    fi
}

# 2. Резервне копіювання конфігурації
backup_config() {
    log "Starting config backup..."
    
    CONFIG_FILE="${BOT_DIR}/.env"
    BACKUP_FILE="${BACKUP_DIR}/bot_env_${TIMESTAMP}"
    
    if [ -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_FILE" "${BACKUP_FILE}"
        gzip "${BACKUP_FILE}"
        
        log "Config backup created: ${BACKUP_FILE}.gz"
        echo "${BACKUP_FILE}.gz"
    else
        log "WARNING: Config file not found"
    fi
}

# 3. Резервне копіювання логів
backup_logs() {
    log "Starting logs backup..."
    
    LOG_ARCHIVE="${BACKUP_DIR}/bot_logs_${TIMESTAMP}.tar.gz"
    
    if [ -d "$LOG_DIR" ]; then
        tar -czf "$LOG_ARCHIVE" -C "$BOT_DIR" logs/
        
        log "Logs backup created: $LOG_ARCHIVE"
        echo "$LOG_ARCHIVE"
    else
        log "WARNING: Logs directory not found"
    fi
}

# 4. Очищення старих резервних копій
cleanup_old_backups() {
    log "Cleaning up old backups (${RETENTION_DAYS} days)..."
    
    find "${BACKUP_DIR}" -type f -name "*.gz" -mtime +${RETENTION_DAYS} -delete
    find "${BACKUP_DIR}" -type f -name "*.db" -mtime +${RETENTION_DAYS} -delete
    
    log "Old backups cleaned up"
}

# Головна функція
main() {
    log "=== Starting backup process ==="
    
    backup_database
    backup_config
    backup_logs
    cleanup_old_backups
    
    log "=== Backup process completed ==="
}

# Запуск
main "$@"
```

### 3.2 Ручне резервне копіювання

```bash
# Швидке резервне копіювання
bash /opt/telegram-bot/docs/scripts/backup.sh

# Тільки база даних
sqlite3 /opt/telegram-bot/data/bot.db ".backup /opt/telegram-bot/backups/bot_emergency.db"

# Тільки конфігурація
cp /opt/telegram-bot/.env /opt/telegram-bot/backups/env_$(date +%Y%m%d)
```

---

## 4. Автоматизація процесу резервного копіювання

### 4.1 Налаштування cron

```bash
# Редагування crontab
crontab -e

# Додати рядки:

# Щоденне резервне копіювання о 2:00
0 2 * * * /opt/telegram-bot/docs/scripts/backup.sh >> /var/log/bot-backup.log 2>&1

# Щотижневе повне резервне копіювання неділі о 3:00
0 3 * * 0 /opt/telegram-bot/docs/scripts/backup.sh --full >> /var/log/bot-backup.log 2>&1

# Перевірка цілісності резервних копій щопонеділка о 4:00
0 4 * * 1 /opt/telegram-bot/docs/scripts/verify_backups.sh >> /var/log/bot-backup-verify.log 2>&1
```

### 4.2 Systemd timer (альтернатива)

```ini
# /etc/systemd/system/bot-backup.timer
[Unit]
Description=Telegram Bot Daily Backup

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/bot-backup.service
[Unit]
Description=Telegram Bot Backup Service

[Service]
Type=oneshot
User=botuser
ExecStart=/opt/telegram-bot/docs/scripts/backup.sh
```

---

## 5. Перевірка цілісності резервних копій

### 5.1 Скрипт перевірки

```bash
#!/bin/bash
# verify_backups.sh - Перевірка цілісності резервних копій

set -e

BACKUP_DIR="/opt/telegram-bot/backups"
ERRORS=0

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

check_database_backup() {
    log "Checking database backups..."
    
    for backup in "${BACKUP_DIR}"/*_db_*.db.gz; do
        if [ -f "$backup" ]; then
            # Розпакування для перевірки
            temp_file=$(mktemp)
            gunzip -c "$backup" > "$temp_file"
            
            # Перевірка цілісності SQLite
            if sqlite3 "$temp_file" "PRAGMA integrity_check;" | grep -q "ok"; then
                log "OK: $(basename $backup)"
            else
                log "ERROR: $(basename $backup) - integrity check failed"
                ERRORS=$((ERRORS + 1))
            fi
            
            rm "$temp_file"
        fi
    done
}

check_config_backup() {
    log "Checking config backups..."
    
    for backup in "${BACKUP_DIR}"/*_env_*.gz; do
        if [ -f "$backup" ]; then
            # Перевірка, що файл не порожній
            if gunzip -c "$backup" | grep -q "BOT_TOKEN"; then
                log "OK: $(basename $backup)"
            else
                log "ERROR: $(basename $backup) - invalid config"
                ERRORS=$((ERRORS + 1))
            fi
        fi
    done
}

check_log_backup() {
    log "Checking log archives..."
    
    for backup in "${BACKUP_DIR}"/*_logs_*.tar.gz; do
        if [ -f "$backup" ]; then
            # Перевірка архіву
            if tar -tzf "$backup" > /dev/null 2>&1; then
                log "OK: $(basename $backup)"
            else
                log "ERROR: $(basename $backup) - corrupted archive"
                ERRORS=$((ERRORS + 1))
            fi
        fi
    done
}

generate_report() {
    log "=== Backup Verification Report ==="
    log "Total errors: $ERRORS"
    
    if [ $ERRORS -gt 0 ]; then
        # Відправка сповіщення адміну (опціонально)
        # curl -X POST "https://hooks.slack.com/services/..." -d "text='Backup verification failed: $ERRORS errors'"
        log "WARNING: Some backups have issues"
    else
        log "SUCCESS: All backups verified"
    fi
}

main() {
    log "=== Starting backup verification ==="
    
    check_database_backup
    check_config_backup
    check_log_backup
    generate_report
    
    exit $ERRORS
}

main "$@"
```

---

## 6. Процедура відновлення

### 6.1 Повне відновлення системи

```bash
#!/bin/bash
# restore.sh - Скрипт відновлення

set -e

BACKUP_DIR="/opt/telegram-bot/backups"
DATA_DIR="/opt/telegram-bot/data"
TIMESTAMP="$1"

if [ -z "$TIMESTAMP" ]; then
    echo "Usage: $0 <timestamp YYYYMMDD_HHMMSS>"
    echo "Available backups:"
    ls -la "${BACKUP_DIR}"/*_db_*.db.gz | awk '{print $9}' | xargs -I {} basename {}
    exit 1
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Зупинка сервісу
log "Stopping bot service..."
sudo systemctl stop telegram-bot.service

# Відновлення бази даних
log "Restoring database..."
DB_BACKUP="${BACKUP_DIR}/bot_db_${TIMESTAMP}.db.gz"

if [ -f "$DB_BACKUP" ]; then
    # Створення резервної копії поточної бази
    cp "${DATA_DIR}/bot.db" "${DATA_DIR}/bot.db.broken_$(date +%Y%m%d_%H%M%S)"
    
    # Відновлення
    gunzip -c "$DB_BACKUP" > "${DATA_DIR}/bot.db"
    chmod 640 "${DATA_DIR}/bot.db"
    
    log "Database restored from: $DB_BACKUP"
else
    log "ERROR: Backup not found: $DB_BACKUP"
    exit 1
fi

# Відновлення конфігурації (опціонально)
log "Restoring config (optional)..."
read -p "Restore config? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    CONFIG_BACKUP="${BACKUP_DIR}/bot_env_${TIMESTAMP}.gz"
    if [ -f "$CONFIG_BACKUP" ]; then
        gunzip -c "$CONFIG_BACKUP" > "${BOT_DIR}/.env"
        log "Config restored"
    fi
fi

# Запуск сервісу
log "Starting bot service..."
sudo systemctl start telegram-bot.service

# Перевірка
sleep 5
sudo systemctl status telegram-bot.service

log "=== Restore completed ==="
```

### 6.2 Вибіркове відновлення даних

```bash
# Відновлення тільки окремих таблиць (SQLite)
sqlite3 /opt/telegram-bot/data/bot.db "
.mode insert
.import /tmp/users_data.txt users
"

# Відновлення з SQL dump
sqlite3 /opt/telegram-bot/data/bot.db < /opt/telegram-bot/backups/tables/users_backup.sql
```

### 6.3 Відновлення логів

```bash
# Розпакування логів
tar -xzf /opt/telegram-bot/backups/bot_logs_20240115_030000.tar.gz -C /tmp/

# Перегляд логів
cat /tmp/logs/bot.log
```

---

## 7. Зберігання та ротація копій

### 7.1 Локальне зберігання

```bash
# Структура директорії резервних копій
ls -la /opt/telegram-bot/backups/

# Очікувана структура файлів:
# bot_db_20240115_020000.db.gz
# bot_env_20240115_020000.gz
# bot_logs_20240115_020000.tar.gz
```

### 7.2 Віддалене зберігання (S3)

```bash
#!/bin/bash
# sync_to_s3.sh - Синхронізація з AWS S3

AWS_BUCKET="my-bot-backups"
AWS_REGION="eu-central-1"

# Встановлення AWS CLI
pip install awscli

# Налаштування credentials
aws configure

# Синхронізація
aws s3 sync /opt/telegram-bot/backups/ s3://${AWS_BUCKET}/bot/ \
    --storage-class STANDARD_IA \
    --sse AES256 \
    --region ${AWS_REGION}

# Перевірка
aws s3 ls s3://${AWS_BUCKET}/bot/
```

### 7.3 Ротація копій

```bash
# Скрипт ротації ( retention policy )
#!/bin/bash
# rotate_backups.sh

S3_BUCKET="s3://my-bot-backups/bot/"
LOCAL_DIR="/opt/telegram-bot/backups"

# Видалення старих локальних копій (понад 30 днів)
find ${LOCAL_DIR} -type f -mtime +30 -delete

# Видалення старих S3 копій (понад 90 днів)
aws s3 ls ${S3_BUCKET} | while read -r line; do
    createDate=$(echo "$line" | awk '{print $1" "$2}')
    createDate=$(date -d "$createDate" +%s)
    olderThan=$(date -d "-90 days" +%s)
    
    if [ $createDate -lt $olderThan ]; then
        fileName=$(echo "$line" | awk '{print $4}')
        aws s3 rm "${S3_BUCKET}${fileName}"
        echo "Deleted: $fileName"
    fi
done
```

---

## 8. Тестування відновлення

### 8.1 Регулярне тестування

```bash
#!/bin/bash
# test_restore.sh - Тестування відновлення

set -e

BACKUP_DIR="/opt/telegram-bot/backups"
TEST_DIR="/tmp/restore_test"
TIMESTAMP="$1"

mkdir -p "${TEST_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Останній backup
if [ -z "$TIMESTAMP" ]; then
    TIMESTAMP=$(ls -1t "${BACKUP_DIR}"/bot_db_*.db.gz 2>/dev/null | head -1 | grep -oP '\d{8}_\d{6}')
fi

log "Testing restore from backup: $TIMESTAMP"

# Розпакування
DB_BACKUP="${BACKUP_DIR}/bot_db_${TIMESTAMP}.db.gz"
gunzip -c "$DB_BACKUP" > "${TEST_DIR}/test.db"

# Перевірка
log "Verifying database..."
if sqlite3 "${TEST_DIR}/test.db" "SELECT COUNT(*) FROM users;" > /dev/null 2>&1; then
    USER_COUNT=$(sqlite3 "${TEST_DIR}/test.db" "SELECT COUNT(*) FROM users;")
    log "OK: Database has $USER_COUNT users"
else
    log "ERROR: Database verification failed"
    exit 1
fi

# Перевірка таблиць
log "Checking tables..."
TABLES=$(sqlite3 "${TEST_DIR}/test.db" ".tables")
log "Tables found: $TABLES"

# Очищення
rm -rf "${TEST_DIR}"

log "=== Restore test completed successfully ==="
```

### 8.2 Чек-лист тестування

- [ ] Резервна копія створюється без помилок
- [ ] Цілісність даних перевіряється
- [ ] Відновлення працює коректно
- [ ] Всі таблиці присутні
- [ ] Дані відповідають очікуваним
- [ ] Логи архівуються правильно
- [ ] Віддалене копіювання працює

---

## 9. Аварійне відновлення

### 9.1 Повний відказ сервера

```bash
# 1. Підготовка нового сервера
# 2. Встановлення залежностей
# 3. Клонування проекту
# 4. Відновлення конфігурації
# 5. Відновлення бази даних
# 6. Запуск сервісу
```

### 9.2 Відновлення з віддаленого сховища

```bash
# Завантаження останньої резервної копії з S3
aws s3 cp s3://my-bot-backups/bot/bot_db_latest.db.gz /opt/telegram-bot/backups/

# Відновлення
gunzip -c /opt/telegram-bot/backups/bot_db_latest.db.gz > /opt/telegram-bot/data/bot.db
```

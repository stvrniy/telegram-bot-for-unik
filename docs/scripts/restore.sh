#!/bin/bash
# restore.sh - Скрипт відновлення з резервної копії

set -e

BACKUP_DIR="/opt/telegram-bot/backups"
DATA_DIR="/opt/telegram-bot/data"
BOT_DIR="/opt/telegram-bot"
TIMESTAMP="$1"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

show_usage() {
    echo "Usage: $0 <timestamp YYYYMMDD_HHMMSS>"
    echo ""
    echo "Available database backups:"
    ls -1t "${BACKUP_DIR}"/bot_db_*.db.gz 2>/dev/null | head -5 | while read f; do
        basename "$f" | sed 's/bot_db_//; s/.db.gz//'
    done
    exit 1
}

# Перевірка аргументів
if [ -z "$TIMESTAMP" ]; then
    show_usage
fi

log "=== Starting restore from backup: $TIMESTAMP ==="

# Перевірка наявності резервної копії
DB_BACKUP="${BACKUP_DIR}/bot_db_${TIMESTAMP}.db.gz"
if [ ! -f "$DB_BACKUP" ]; then
    log "ERROR: Backup not found: $DB_BACKUP"
    show_usage
fi

# Зупинка сервісу
log "Stopping bot service..."
sudo systemctl stop telegram-bot.service || true

# Створення резервної копії поточної бази (на випадок відкату)
if [ -f "${DATA_DIR}/bot.db" ]; then
    CURRENT_BACKUP="${DATA_DIR}/bot.db.pre_restore_$(date +%Y%m%d_%H%M%S)"
    cp "${DATA_DIR}/bot.db" "$CURRENT_BACKUP"
    log "Current database backed up to: $CURRENT_BACKUP"
fi

# Відновлення бази даних
log "Restoring database..."
gunzip -c "$DB_BACKUP" > "${DATA_DIR}/bot.db"
chmod 640 "${DATA_DIR}/bot.db"

# Перевірка відновленої бази
log "Verifying restored database..."
if sqlite3 "${DATA_DIR}/bot.db" "PRAGMA integrity_check;" | grep -q "ok"; then
    log "OK: Database integrity verified"
else
    log "ERROR: Database integrity check failed!"
    log "Restoring original database..."
    mv "$CURRENT_BACKUP" "${DATA_DIR}/bot.db"
    exit 1
fi

# Відновлення конфігурації (опціонально)
log ""
log "Config backup found:"
ls -1 "${BACKUP_DIR}"/bot_env_${TIMESTAMP}*.gz 2>/dev/null | while read f; do
    log "  - $(basename $f)"
done

read -p "Restore config files? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    for config_backup in "${BACKUP_DIR}"/bot_env_${TIMESTAMP}*.gz; do
        if [ -f "$config_backup" ]; then
            gunzip -c "$config_backup" > "${BOT_DIR}/.env"
            log "Config restored: $(basename $config_backup)"
        fi
    done
fi

# Запуск сервісу
log "Starting bot service..."
sudo systemctl start telegram-bot.service

# Перевірка
sleep 5
if sudo systemctl is-active --quiet telegram-bot.service; then
    log "OK: Bot service is running"
else
    log "WARNING: Bot service may not have started correctly"
    sudo systemctl status telegram-bot.service
fi

log "=== Restore completed ==="

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

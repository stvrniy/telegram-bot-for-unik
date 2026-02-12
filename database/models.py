"""
Database models and operations for the Telegram Education Bot.
Uses SQLite with context managers for safe database handling.
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional, List, Generator
from enum import Enum

from config.settings import settings

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User roles for access control."""
    STUDENT = "student"
    GROUP_LEADER = "group_leader"  # Старсота
    TEACHER = "teacher"
    ADMIN = "admin"


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.
    Ensures proper connection closing even on errors.
    """
    db_path = settings.get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initialize database tables and indexes."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users table with extended roles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                group_name TEXT,
                full_name TEXT,
                role TEXT DEFAULT 'student',
                is_admin INTEGER DEFAULT 0,
                notifications_enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                title TEXT NOT NULL,
                room TEXT,
                group_name TEXT NOT NULL,
                teacher_id INTEGER,
                lesson_type TEXT DEFAULT 'lecture',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Messages table for user-to-user communication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(user_id),
                FOREIGN KEY (recipient_id) REFERENCES users(user_id)
            )
        ''')
        
        # Teacher-subject assignments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                subject_name TEXT NOT NULL,
                group_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES users(user_id)
            )
        ''')
        
        # Subjects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                short_name TEXT,
                credits INTEGER DEFAULT 0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Group subjects (subjects assigned to groups)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                subject_name TEXT NOT NULL,
                teacher_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_subjects_name 
            ON subjects(name)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_group_subjects_group 
            ON group_subjects(group_name)
        ''')
        # Create indexes for better performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_events_group_date 
            ON events(group_name, date)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_group 
            ON users(group_name)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_recipient 
            ON messages(recipient_id, is_read)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_role 
            ON users(role)
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully with extended roles")


def add_user(
    user_id: int, 
    group_name: Optional[str] = None, 
    is_admin: int = 0,
    full_name: Optional[str] = None,
    role: str = "student"
) -> None:
    """Add or update a user in the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, group_name, full_name, role, is_admin, notifications_enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        ''', (user_id, group_name, full_name, role, is_admin))
        conn.commit()


def get_user(user_id: int) -> Optional[sqlite3.Row]:
    """Get user data by user_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()


def update_user_group(user_id: int, group_name: str) -> bool:
    """Update user's group name."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET group_name = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', 
            (group_name, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def update_user_name(user_id: int, full_name: str) -> bool:
    """Update user's full name."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET full_name = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', 
            (full_name, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def update_user_role(user_id: int, role: str) -> bool:
    """Update user's role."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', 
            (role, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def toggle_notifications(user_id: int, enabled: bool) -> bool:
    """Toggle user notifications on/off."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET notifications_enabled = ? WHERE user_id = ?', 
            (1 if enabled else 0, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_users_for_group(group_name: str) -> List[sqlite3.Row]:
    """Get all users in a group with notifications enabled."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM users WHERE group_name = ? AND notifications_enabled = 1',
            (group_name,)
        )
        return cursor.fetchall()


def get_group_leader(group_name: str) -> Optional[sqlite3.Row]:
    """Get the group leader (старсота) for a group."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM users WHERE group_name = ? AND role = ?',
            (group_name, UserRole.GROUP_LEADER.value)
        )
        return cursor.fetchone()


def get_users_by_role(role: str) -> List[sqlite3.Row]:
    """Get all users with a specific role."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE role = ?', (role,))
        return cursor.fetchall()


def get_users_by_name(full_name: str) -> List[sqlite3.Row]:
    """Search users by name (partial match)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT user_id, group_name, full_name, role FROM users WHERE full_name LIKE ?',
            (f"%{full_name}%",)
        )
        return cursor.fetchall()


def add_event(
    date: str, 
    time: str, 
    title: str, 
    room: str, 
    group_name: str,
    teacher_id: Optional[int] = None,
    lesson_type: str = "lecture"
) -> int:
    """Add a new event and return its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (date, time, title, room, group_name, teacher_id, lesson_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (date, time, title, room, group_name, teacher_id, lesson_type))
        conn.commit()
        return cursor.lastrowid


def get_events(
    group_name: str, 
    date: Optional[str] = None
) -> List[sqlite3.Row]:
    """Get events for a group, optionally filtered by date."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if date:
            if group_name:
                cursor.execute(
                    'SELECT * FROM events WHERE group_name = ? AND date = ? ORDER BY time',
                    (group_name, date)
                )
            else:
                cursor.execute(
                    'SELECT * FROM events WHERE date = ? ORDER BY time',
                    (date,)
                )
        else:
            if group_name:
                cursor.execute(
                    'SELECT * FROM events WHERE group_name = ? ORDER BY date, time',
                    (group_name,)
                )
            else:
                cursor.execute(
                    'SELECT * FROM events ORDER BY date, time'
                )
        return cursor.fetchall()


def get_all_events() -> List[sqlite3.Row]:
    """Get all events."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM events ORDER BY date, time')
        return cursor.fetchall()


def get_events_for_date(date: str) -> List[sqlite3.Row]:
    """Get all events for a specific date."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM events WHERE date = ?', (date,))
        return cursor.fetchall()


def edit_event(
    event_id: int, 
    date: str, 
    time: str, 
    title: str, 
    room: str, 
    group_name: str,
    teacher_id: Optional[int] = None,
    lesson_type: str = "lecture"
) -> bool:
    """Edit an existing event."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE events SET date = ?, time = ?, title = ?, room = ?, group_name = ?, 
            teacher_id = ?, lesson_type = ? WHERE id = ?
        ''', (date, time, title, room, group_name, teacher_id, lesson_type, event_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_event(event_id: int) -> bool:
    """Delete an event by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
        conn.commit()
        return cursor.rowcount > 0


# Messaging functions
def send_message(
    sender_id: int, 
    recipient_id: int, 
    message: str
) -> int:
    """Send a message from one user to another."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (sender_id, recipient_id, message)
            VALUES (?, ?, ?)
        ''', (sender_id, recipient_id, message))
        conn.commit()
        return cursor.lastrowid


def get_messages(user_id: int, unread_only: bool = False) -> List[sqlite3.Row]:
    """Get messages for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if unread_only:
            cursor.execute(
                '''SELECT m.*, u.full_name as sender_name 
                   FROM messages m 
                   JOIN users u ON m.sender_id = u.user_id 
                   WHERE m.recipient_id = ? AND m.is_read = 0
                   ORDER BY m.created_at DESC''',
                (user_id,)
            )
        else:
            cursor.execute(
                '''SELECT m.*, u.full_name as sender_name 
                   FROM messages m 
                   JOIN users u ON m.sender_id = u.user_id 
                   WHERE m.recipient_id = ?
                   ORDER BY m.created_at DESC''',
                (user_id,)
            )
        return cursor.fetchall()


def mark_message_read(message_id: int) -> bool:
    """Mark a message as read."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE messages SET is_read = 1 WHERE id = ?', (message_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_unread_count(user_id: int) -> int:
    """Get count of unread messages for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM messages WHERE recipient_id = ? AND is_read = 0',
            (user_id,)
        )
        return cursor.fetchone()[0]


# Teacher-subject functions
def assign_subject_to_teacher(
    teacher_id: int, 
    subject_name: str, 
    group_name: str
) -> int:
    """Assign a subject to a teacher for a specific group."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO teacher_subjects (teacher_id, subject_name, group_name)
            VALUES (?, ?, ?)
        ''', (teacher_id, subject_name, group_name))
        conn.commit()
        return cursor.lastrowid


def get_teacher_subjects(teacher_id: int) -> List[sqlite3.Row]:
    """Get all subjects assigned to a teacher."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM teacher_subjects WHERE teacher_id = ?',
            (teacher_id,)
        )
        return cursor.fetchall()


# Subject management functions
def add_subject(name: str, short_name: str = None, credits: int = 0, description: str = None) -> int:
    """Add a new subject to the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO subjects (name, short_name, credits, description)
            VALUES (?, ?, ?, ?)
        ''', (name, short_name, credits, description))
        conn.commit()
        return cursor.lastrowid


def get_all_subjects() -> List[sqlite3.Row]:
    """Get all subjects from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subjects ORDER BY name')
        return cursor.fetchall()


def get_subject_by_name(name: str) -> Optional[sqlite3.Row]:
    """Get a subject by name."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM subjects WHERE name = ?', (name,))
        return cursor.fetchone()


def delete_subject(subject_id: int) -> bool:
    """Delete a subject by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM subjects WHERE id = ?', (subject_id,))
        conn.commit()
        return cursor.rowcount > 0


# Group-subject functions for group leaders and teachers
def add_group_subject(group_name: str, subject_name: str, teacher_name: str = None) -> int:
    """Add a subject to a group."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO group_subjects (group_name, subject_name, teacher_name)
            VALUES (?, ?, ?)
        ''', (group_name, subject_name, teacher_name))
        conn.commit()
        return cursor.lastrowid


def get_group_subjects(group_name: str) -> List[sqlite3.Row]:
    """Get all subjects for a group."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM group_subjects WHERE group_name = ? ORDER BY subject_name',
            (group_name,)
        )
        return cursor.fetchall()


def delete_group_subject(group_name: str, subject_name: str) -> bool:
    """Delete a subject from a group."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM group_subjects WHERE group_name = ? AND subject_name = ?',
            (group_name, subject_name)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_subject_info(subject_name: str) -> dict:
    """Get information about a subject."""
    # First try to get from database
    subject = get_subject_by_name(subject_name)
    
    if subject:
        return {
            'name': subject['name'] if isinstance(subject, dict) else subject[1],
            'short_name': subject['short_name'] if isinstance(subject, dict) else subject[2],
            'credits': subject['credits'] if isinstance(subject, dict) else subject[3],
            'description': subject['description'] if isinstance(subject, dict) else subject[4],
            'topics': []
        }
    
    # Fallback to mock data
    subjects_info = {
        "Вища математика": {
            "name": "Вища математика",
            "short_name": "ВМ",
            "credits": 4,
            "description": "Курс вищої математики для технічних спеціальностей",
            "topics": ["Лінійна алгебра", "Аналітична геометрія", "Математичний аналіз"]
        },
        "Програмування": {
            "name": "Програмування",
            "short_name": "Прог",
            "credits": 8,
            "description": "Основи програмування на мові Python",
            "topics": ["Базові конструкції", "Функції", "ООП", "Робота з файлами"]
        },
        "Дискретна математика": {
            "name": "Дискретна математика",
            "short_name": "ДМ",
            "credits": 4,
            "description": "Дискретна математика для комп'ютерних наук",
            "topics": ["Комбінаторика", "Графи", "Логіка", "Теорія алгоритмів"]
        },
        "Алгоритми та структури даних": {
            "name": "Алгоритми та структури даних",
            "short_name": "АСД",
            "credits": 6,
            "description": "Алгоритми та основні структури даних",
            "topics": ["Сортування", "Пошук", "Графи", "Динамічне програмування"]
        },
        "Бази даних": {
            "name": "Бази даних",
            "short_name": "БД",
            "credits": 5,
            "description": "Проектування та використання баз даних",
            "topics": ["Реляційна модель", "SQL", "Нормалізація", "Транзакції"]
        },
    }
    return subjects_info.get(subject_name, {
        "name": subject_name,
        "short_name": subject_name[:3],
        "credits": 0,
        "description": "Інформація про предмет відсутня",
        "topics": []
    })


def get_stats() -> dict:
    """Get bot statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        stats = {
            'total_users': 0,
            'students': 0,
            'group_leaders': 0,
            'teachers': 0,
            'admins': 0,
            'notifications_enabled': 0,
            'groups_count': 0,
            'events_count': 0,
            'unread_messages': 0
        }
        
        cursor.execute('SELECT COUNT(*) FROM users')
        stats['total_users'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
        stats['students'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'group_leader'")
        stats['group_leaders'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'teacher'")
        stats['teachers'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        stats['admins'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE notifications_enabled = 1')
        stats['notifications_enabled'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT group_name) FROM users WHERE group_name IS NOT NULL')
        stats['groups_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM events')
        stats['events_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM messages WHERE is_read = 0')
        stats['unread_messages'] = cursor.fetchone()[0]
        
        return stats


def get_all_users() -> List[sqlite3.Row]:
    """Get all users ordered by group and name."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY group_name, full_name')
        return cursor.fetchall()

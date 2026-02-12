import pytest
import sqlite3
import sys
import os

# Додаємо корінь проекту до шляху Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def simple_db():
    """Проста фікстура бази даних для ізоляції тестів"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Створюємо таблиці (відповідно до schema в models.py)
    cursor.execute('''
    CREATE TABLE users (
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
    
    cursor.execute('''
    CREATE TABLE events (
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
    
    cursor.execute('''
    CREATE TABLE subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        short_name TEXT,
        credits INTEGER DEFAULT 0,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE group_subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT NOT NULL,
        subject_name TEXT NOT NULL,
        teacher_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Додаємо тестові дані
    cursor.executemany(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        [
            (123456789, 'КС-21', 'Іван Іванов', 'student', 0, 1),
            (987654321, 'КС-21', 'Петро Петренко', 'student', 0, 0),
            (555555555, 'ІН-23', 'Марія Сидоренко', 'student', 0, 1),
            (111111111, 'КС-21', 'Староста', 'group_leader', 0, 1),
            (222222222, None, 'Викладач', 'teacher', 0, 1),
        ]
    )
    
    cursor.executemany(
        "INSERT INTO events (date, time, title, room, group_name, teacher_id, lesson_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ('2025-09-16', '10:00', 'Математика', '301', 'КС-21', None, 'lecture'),
            ('2025-09-16', '12:00', 'Фізика', '201', 'КС-21', None, 'lecture'),
            ('2025-09-17', '09:00', 'Програмування', '101', 'ІН-23', None, 'practice'),
        ]
    )
    
    # Додаємо предмети
    cursor.executemany(
        "INSERT INTO subjects (name, short_name, credits, description) VALUES (?, ?, ?, ?)",
        [
            ('Вища математика', 'ВМ', 4, 'Курс вищої математики'),
            ('Програмування', 'Прог', 8, 'Основи програмування'),
        ]
    )
    
    # Додаємо предмети груп
    cursor.executemany(
        "INSERT INTO group_subjects (group_name, subject_name, teacher_name) VALUES (?, ?, ?)",
        [
            ('КС-21', 'Вища математика', 'Петров П.П.'),
            ('КС-21', 'Програмування', 'Іванов І.І.'),
        ]
    )
    
    conn.commit()
    yield conn
    conn.close()


def test_get_events_function(simple_db):
    """Тест вимоги R1.1 - отримання розкладу занять для групи"""
    import database.models as models
    
    # Тимчасово замінюємо get_db_connection
    original_get_conn = models.get_db_connection
    models.get_db_connection = lambda: simple_db
    
    try:
        # Act: викликаємо реальну функцію з models.py
        events = models.get_events('КС-21')
        
        # Assert: перевіряємо, що система коректно повертає розклад
        assert len(events) == 2  # Має бути 2 події для групи КС-21
        assert events[0][3] == 'Математика'  # title першої події
        assert events[1][3] == 'Фізика'      # title другої події
        
        # Додаткова перевірка структури даних
        for event in events:
            assert len(event) == 8  # id, date, time, title, room, group_name, teacher_id, lesson_type
            assert event[5] == 'КС-21'  # Всі події мають належати групі КС-21
        
    finally:
        models.get_db_connection = original_get_conn


def test_get_users_for_group_function(simple_db):
    """Тест вимоги R1.2 - отримання користувачів для сповіщень"""
    import database.models as models
    
    original_get_conn = models.get_db_connection
    models.get_db_connection = lambda: simple_db
    
    try:
        # Act: викликаємо реальну функцію
        users = models.get_users_for_group('КС-21')
        
        # Assert: перевіряємо, що система знаходить користувачів з увімкненими сповіщеннями
        assert len(users) == 2  # Два користувачі з увімкненими сповіщеннями
        user_ids = [user[0] for user in users]
        assert 123456789 in user_ids  # Іван Іванов
        assert 111111111 in user_ids  # Староста
        
        # Перевіряємо, що користувач з вимкненими сповіщеннями не повертається
        assert 987654321 not in user_ids  # Петро Петренко має вимкнені сповіщення
        
    finally:
        models.get_db_connection = original_get_conn


def test_get_events_for_date_function(simple_db):
    """Тест вимоги R1.1 - отримання розкладу на конкретну дату"""
    import database.models as models
    
    original_get_conn = models.get_db_connection
    models.get_db_connection = lambda: simple_db
    
    try:
        # Act: викликаємо реальну функцію
        events = models.get_events_for_date('2025-09-16')
        
        # Assert: перевіряємо, що система коректно повертає події на дату
        assert len(events) == 2  # Має бути 2 події на 2025-09-16
        assert all(event[1] == '2025-09-16' for event in events)  # Всі події мають потрібну дату
        
        # Перевіряємо, що подія з іншої дати не повертається
        event_dates = [event[1] for event in events]
        assert '2025-09-17' not in event_dates  # Подія з 17 вересня не має бути в результаті
        
    finally:
        models.get_db_connection = original_get_conn


def test_get_events_with_date_filter(simple_db):
    """Тест вимоги R1.1 - отримання розкладу для групи з фільтром по даті"""
    import database.models as models
    
    original_get_conn = models.get_db_connection
    models.get_db_connection = lambda: simple_db
    
    try:
        # Act: викликаємо функцію з фільтром по даті
        events = models.get_events('КС-21', '2025-09-16')
        
        # Assert: перевіряємо коректність фільтрації
        assert len(events) == 2  # Всі 2 події КС-21 на цю дату
        assert all(event[1] == '2025-09-16' for event in events)
        assert all(event[5] == 'КС-21' for event in events)
        
    finally:
        models.get_db_connection = original_get_conn


def test_get_group_subjects_function(simple_db):
    """Тест отримання предметів групи"""
    import database.models as models
    
    original_get_conn = models.get_db_connection
    models.get_db_connection = lambda: simple_db
    
    try:
        # Act: викликаємо функцію
        subjects = models.get_group_subjects('КС-21')
        
        # Assert: перевіряємо, що система повертає предмети групи
        assert len(subjects) == 2  # КС-21 має 2 предмети
        
        # Перевіряємо, що предмети правильні
        subject_names = [s[1] for s in subjects]
        assert 'Вища математика' in subject_names
        assert 'Програмування' in subject_names
        
    finally:
        models.get_db_connection = original_get_conn


def test_add_subject_function(simple_db):
    """Тест додавання предмету"""
    import database.models as models
    
    original_get_conn = models.get_db_connection
    models.get_db_connection = lambda: simple_db
    
    try:
        # Act: додаємо новий предмет
        subject_id = models.add_subject(
            name='Фізика',
            short_name='Фіз',
            credits=5,
            description='Загальна фізика'
        )
        
        # Assert: перевіряємо, що предмет додано
        assert subject_id is not None or subject_id > 0
        
        # Перевіряємо, що предмет можна отримати
        subject = models.get_subject_by_name('Фізика')
        assert subject is not None
        assert subject[1] == 'Фізика'  # name
        assert subject[2] == 'Фіз'  # short_name
        assert subject[3] == 5  # credits
        
    finally:
        models.get_db_connection = original_get_conn


def test_get_user_function(simple_db):
    """Тест отримання користувача"""
    import database.models as models
    
    original_get_conn = models.get_db_connection
    models.get_db_connection = lambda: simple_db
    
    try:
        # Act: отримуємо користувача
        user = models.get_user(123456789)
        
        # Assert: перевіряємо, що користувач знайдено
        assert user is not None
        assert user[0] == 123456789  # user_id
        assert user[1] == 'КС-21'  # group_name
        assert user[2] == 'Іван Іванов'  # full_name
        assert user[3] == 'student'  # role
        
    finally:
        models.get_db_connection = original_get_conn


def test_update_user_role_function(simple_db):
    """Тест оновлення ролі користувача"""
    import database.models as models
    
    original_get_conn = models.get_db_connection
    models.get_db_connection = lambda: simple_db
    
    try:
        # Act: змінюємо роль користувача
        success = models.update_user_role(123456789, 'group_leader')
        
        # Assert: перевіряємо, що роль змінено
        assert success is True
        
        # Перевіряємо, що роль дійсно змінилася
        user = models.get_user(123456789)
        assert user[3] == 'group_leader'
        
    finally:
        models.get_db_connection = original_get_conn


def test_delete_event_function(simple_db):
    """Тест видалення події"""
    import database.models as models
    
    original_get_conn = models.get_db_connection
    models.get_db_connection = lambda: simple_db
    
    try:
        # Спочатку отримуємо подію
        events = models.get_events('КС-21')
        assert len(events) == 2
        
        # Act: видаляємо подію
        event_id = events[0][0]
        success = models.delete_event(event_id)
        
        # Assert: перевіряємо, що подію видалено
        assert success is True
        
        # Перевіряємо, що подій стало менше
        events = models.get_events('КС-21')
        assert len(events) == 1
        
    finally:
        models.get_db_connection = original_get_conn


def test_get_all_events_function(simple_db):
    """Тест отримання всіх подій"""
    import database.models as models
    
    original_get_conn = models.get_db_connection
    models.get_db_connection = lambda: simple_db
    
    try:
        # Act: отримуємо всі події
        events = models.get_all_events()
        
        # Assert: перевіряємо, що всі події повернуто
        assert len(events) == 3  # Всі 3 події
        
    finally:
        models.get_db_connection = original_get_conn

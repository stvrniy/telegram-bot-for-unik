import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config.settings import settings
from database.models import get_users_by_name, add_event, get_events, edit_event, delete_event, get_all_events, get_users_for_group, update_user_role, get_user
from datetime import datetime
from utils.decorators import admin_only

logger = logging.getLogger(__name__)

router = Router()

class NotifyGroupStates(StatesGroup):
    waiting_for_group = State()
    waiting_for_message = State()

@router.message(Command("admin_help"))
@router.message(Command("admin_commands"))
@admin_only
async def admin_help_command(message: Message):
    help_text = (
        "👨‍💼 *Список всіх адмін-команд:*\n\n"
        "📤 Робота з розкладом:\n"
        "`/upload_ics` - завантажити розклад з .ics файлу\n"
        "`/schedule_week` - розклад на тиждень\n"
        "`/tomorrow` - розклад на завтра\n"
        "`/clear_schedule` - очистити розклад\n\n"
        "📅 Робота з подіями:\n"
        "`/add_event <дата> <час> <назва> <аудиторія> <група>` - додати подію\n"
        "`/edit_event <id> <дата> <час> <назва> <аудиторія> <група>` - редагувати подію\n"
        "`/delete_event <id>` - видалити подію\n"
        "`/all_events` - переглянути всі події\n\n"
        "📚 Робота з предметами:\n"
        "`/add_subject` - додати предмет до групи\n"
        "`/my_subjects` - переглянути предмети групи\n\n"
        "📢 Повідомлення:\n"
        "`/notify_group` - відправити повідомлення всій групі\n"
        "`/notify_student` - відправити повідомлення конкретному студенту\n"
        "`/list_students` - список всіх студентів\n\n"
        "👥 Управління ролями:\n"
        "`/set_user_role <user_id> <роль>` - призначити роль\n"
        "`/get_user_role <user_id>` - переглянути роль\n\n"
        "📊 Статистика:\n"
        "`/stats` - статистика користувачів\n\n"
        "ℹ️ Довідка:\n"
        "`/admin_help` - ця довідка\n"
        "`/admin_commands` - список адмін-команд\n\n"
        "👥 Звичайні команди також доступні:\n"
        "`/help` - довідка для студдентів"
    )
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("notify_group"))
@admin_only
async def notify_group_command(message: Message, state: FSMContext):
    await message.answer("👥 Введіть назву групи для повідомлення:")
    await state.set_state(NotifyGroupStates.waiting_for_group)

@router.message(NotifyGroupStates.waiting_for_group)
async def process_notify_group(message: Message, state: FSMContext):
    group_name = message.text.strip()
    await state.update_data(group_name=group_name)
    await message.answer("💬 Введіть повідомлення для групи:")
    await state.set_state(NotifyGroupStates.waiting_for_message)

@router.message(NotifyGroupStates.waiting_for_message)
async def process_group_message(message: Message, state: FSMContext):
    data = await state.get_data()
    group_name = data.get('group_name')
    text = message.text
    
    users = get_users_for_group(group_name)
    
    if not users:
        await message.answer(f"❌ Не знайдено студентів у групі {group_name}")
        await state.clear()
        return
    
    sent_count = 0
    for user in users:
        try:
            await message.bot.send_message(
                user[0],  # user_id
                f"📢 *Повідомлення для групи {group_name}:*\n\n{text}",
                parse_mode="Markdown"
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Не вдалося відправити повідомлення користувачу {user[0]}: {e}")
    
    await message.answer(f"✅ Повідомлення відправлено {sent_count} студентам групи {group_name}")
    await state.clear()

@router.message(Command("notify_student"))
@admin_only
async def notify_student_command(message: Message):
    """
    Формат: /notify_student Ім'я Прізвище Ваше повідомлення
    """
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "❌ Неправильний формат!\n"
            "Формат: `/notify_student Ім'я Прізвище Ваше повідомлення`\n"
            "Приклад: `/notify_student Іван Іванов Прийди завтра на пару`",
            parse_mode="Markdown"
        )
        return

    full_name, text = args[1], args[2]

    # шукаємо студента по імені
    students = get_users_by_name(full_name)
    if not students:
        await message.answer(f"❌ Студента '{full_name}' не знайдено")
        return

    sent_count = 0
    for student in students:
        try:
            await message.bot.send_message(
                student[0],  # user_id
                f"📢 *Персональне повідомлення від адміністратора:*\n\n{text}",
                parse_mode="Markdown"
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Не вдалося надіслати повідомлення студенту {student[0]}: {e}")

    await message.answer(f"✅ Повідомлення надіслано {sent_count} студентам")

@router.message(Command("list_students"))
@admin_only
async def list_students_command(message: Message):
    from database.models import get_db_connection
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY group_name, full_name')
        users = cursor.fetchall()
    
    if not users:
        await message.answer("📭 Немає зареєстрованих студентів")
        return
    
    response = "👥 *Список всіх студентів:*\n\n"
    
    current_group = None
    for user in users:
        if user[1] != current_group:  # user[1] - group_name
            current_group = user[1]
            response += f"\n🏫 *Група {current_group if current_group else 'Без групи'}:*\n"
        
        response += f"👤 {user[2] if user[2] else 'Без імені'} (ID: {user[0]})\n"
    
    # Розділяємо повідомлення якщо воно занадто довге
    if len(response) > 4000:
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(response, parse_mode="Markdown")

@router.message(Command("stats"))
@admin_only
async def stats_command(message: Message):
    from database.models import get_db_connection
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Отримуємо статистику користувачів
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        admin_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE notifications_enabled = 1')
        notifications_enabled = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT group_name) FROM users WHERE group_name IS NOT NULL')
        groups_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM events')
        events_count = cursor.fetchone()[0]
    
    stats_text = (
        "📊 *Статистика бота:*\n\n"
        f"👥 Загалом користувачів: *{total_users}*\n"
        f"👨‍💼 Адміністраторів: *{admin_users}*\n"
        f"🔔 Сповіщення увімкнено: *{notifications_enabled}*\n"
        f"🏫 Груп: *{groups_count}*\n"
        f"📅 Подій у розкладі: *{events_count}*"
    )
    
    await message.answer(stats_text, parse_mode="Markdown")

@router.message(Command("add_event"))
@admin_only
async def add_event_command(message: Message):
    args = message.text.split(maxsplit=5)
    if len(args) < 6:
        await message.answer("❌ Неправильний формат!\n"
                           "Формат: `/add_event <дата> <час> <назва> <аудиторія> <група>`\n"
                           "Приклад: `/add_event 2025-09-16 10:00 Алгебра 301 КС-21`", 
                           parse_mode="Markdown")
        return
    
    date, time, title, room, group_name = args[1:6]
    
    # Валідація дати
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        await message.answer("❌ Неправильний формат дати! Використовуйте YYYY-MM-DD")
        return
    
    # Валідація часу
    try:
        datetime.strptime(time, "%H:%M")
    except ValueError:
        await message.answer("❌ Неправильний формат часу! Використовуйте HH:MM")
        return
    
    add_event(date, time, title, room, group_name)
    await message.answer(f"✅ Подію додано:\n"
                       f"📝 {title}\n"
                       f"⏰ {time} {date}\n"
                       f"👥 {group_name}\n"
                       f"🏫 Ауд. {room}")

@router.message(Command("edit_event"))
@admin_only
async def edit_event_command(message: Message):
    args = message.text.split(maxsplit=6)
    if len(args) < 7:
        await message.answer("❌ Неправильний формат!\n"
                           "Формат: `/edit_event <id> <дата> <час> <назва> <аудиторія> <група>`",
                           parse_mode="Markdown")
        return
    
    event_id, date, time, title, room, group_name = args[1:7]
    
    try:
        event_id = int(event_id)
    except ValueError:
        await message.answer("❌ ID події має бути числом!")
        return
    
    edit_event(event_id, date, time, title, room, group_name)
    await message.answer(f"✅ Подію #{event_id} відредаговано")

@router.message(Command("delete_event"))
@admin_only
async def delete_event_command(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Неправильний формат!\nФормат: `/delete_event <id>`", parse_mode="Markdown")
        return
    
    event_id = args[1]
    
    try:
        event_id = int(event_id)
    except ValueError:
        await message.answer("❌ ID події має бути числом!")
        return
    
    if delete_event(event_id):
        await message.answer(f"✅ Подію #{event_id} видалено")
    else:
        await message.answer(f"❌ Подію #{event_id} не знайдено")

@router.message(Command("all_events"))
@admin_only
async def all_events_command(message: Message):
    events = get_all_events()
    
    if not events:
        await message.answer("📭 Немає жодної події")
        return
    
    response = "📋 *Всі події:*\n\n"
    for event in events:
        response += f"#{event[0]} {event[1]} {event[2]}: {event[3]} (ауд. {event[4]}) для {event[5]}\n"
    
    # Розділяємо повідомлення якщо воно занадто довге
    if len(response) > 4000:
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(response, parse_mode="Markdown")


# ============ Команди для призначення ролей ============

@router.message(Command("set_user_role"))
@admin_only
async def set_user_role_command(message: Message):
    """
    Призначити роль користувачу.
    Формат: /set_user_role <user_id> <роль>
    
    Доступні ролі:
    - student (за замовчуванням)
    - group_leader (староста)
    - teacher (викладач)
    - admin (адмін)
    """
    from database.models import UserRole
    
    args = message.text.split(maxsplit=2)
    
    if len(args) < 3:
        await message.answer(
            "❌ Неправильний формат!\n\n"
            "Формат: `/set_user_role <user_id> <роль>`\n\n"
            "Доступні ролі:\n"
            "• `student` - студент\n"
            "• `group_leader` - староста\n"
            "• `teacher` - викладач\n"
            "• `admin` - адмін\n\n"
            "Приклад: `/set_user_role 123456789 group_leader`",
            parse_mode="Markdown"
        )
        return
    
    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ user_id має бути числом!")
        return
    
    role_input = args[2].lower().strip()
    
    role_map = {
        'student': UserRole.STUDENT.value,
        'group_leader': UserRole.GROUP_LEADER.value,
        'teacher': UserRole.TEACHER.value,
        'admin': UserRole.ADMIN.value,
    }
    
    if role_input not in role_map:
        await message.answer(
            "❌ Невідома роль!\n\n"
            "Доступні ролі: student, group_leader, teacher, admin",
            parse_mode="Markdown"
        )
        return
    
    role = role_map[role_input]
    
    # Перевіряємо чи користувач існує
    user = get_user(user_id)
    if not user:
        await message.answer(f"❌ Користувач з ID {user_id} не знайдено!")
        return
    
    success = update_user_role(user_id, role)
    
    if success:
        role_names = {
            UserRole.STUDENT.value: '👨‍🎓 Студент',
            UserRole.GROUP_LEADER.value: '👑 Староста',
            UserRole.TEACHER.value: '👨‍🏫 Викладач',
            UserRole.ADMIN.value: '👨‍💼 Адміністратор'
        }
        await message.answer(
            f"✅ Роль призначено!\n\n"
            f"👤 Користувач: {user[2] if user[2] else user_id}\n"
            f"🪪 Нова роль: *{role_names.get(role, role)}*",
            parse_mode="Markdown"
        )
        logger.info(f"User {message.from_user.id} set role {role} for user {user_id}")
    else:
        await message.answer("❌ Помилка при призначенні ролі!")


@router.message(Command("get_user_role"))
@admin_only
async def get_user_role_command(message: Message):
    """
    Переглянути роль користувача.
    Формат: /get_user_role <user_id>
    """
    from database.models import UserRole
    
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "❌ Неправильний формат!\n\n"
            "Формат: `/get_user_role <user_id>`\n\n"
            "Приклад: `/get_user_role 123456789`",
            parse_mode="Markdown"
        )
        return
    
    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ user_id має бути числом!")
        return
    
    user = get_user(user_id)
    
    if not user:
        await message.answer(f"❌ Користувач з ID {user_id} не знайдено!")
        return
    
    role = user[3] if len(user) > 3 else 'student'
    
    role_names = {
        UserRole.STUDENT.value: '👨‍🎓 Студент',
        UserRole.GROUP_LEADER.value: '👑 Староста',
        UserRole.TEACHER.value: '👨‍🏫 Викладач',
        UserRole.ADMIN.value: '👨‍💼 Адміністратор'
    }
    
    await message.answer(
        f"👤 *Інформація про користувача:*\n\n"
        f"🆔 ID: {user_id}\n"
        f"👨‍💼 Ім'я: {user[2] if user[2] else 'Невідомо'}\n"
        f"🏫 Група: {user[1] if user[1] else 'Не вказано'}\n"
        f"🪪 Роль: *{role_names.get(role, role)}*",
        parse_mode="Markdown"
    )

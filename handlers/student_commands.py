"""
Student command handlers for the Telegram Education Bot.
Handles user interactions for viewing and managing schedules.
"""

import logging
import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup

from config.settings import settings
from database.models import (
    add_user,
    get_user,
    update_user_group,
    get_events,
    toggle_notifications,
    update_user_name,
    UserRole,
)
from utils.decorators import format_schedule_message

logger = logging.getLogger(__name__)

router = Router()

# Regex pattern for valid group names (e.g., КС-21, ІП-31)
GROUP_NAME_PATTERN = re.compile(r"^[А-Яа-яA-Za-z]{1,5}-\d{1,3}$")


class UserStates(StatesGroup):
    """FSM states for user interactions."""

    waiting_for_name = State()


@router.message(Command("start"))
async def start_command(message: Message):
    """Handle /start command - welcome new users."""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    is_admin = user_id in settings.ADMIN_IDS

    # Add/update user
    add_user(
        user_id=user_id,
        full_name=message.from_user.full_name,
        is_admin=1 if is_admin else 0,
    )

    role = "👨‍💼 Адміністратор" if is_admin else "👨‍🎓 Студент"

    welcome_text = (
        f"👋 Вітаю, {username}!\n\n"
        f"📚 Я бот для відстеження розкладу занять СумДУ\n"
        f"🪪 Ваша роль: {role}\n\n"
        "📋 *Доступні команди:*\n\n"
        "🏫 Встановити групу:\n"
        "`/setgroup <назва_групи>`\n"
        "Приклад: `/setgroup КС-21`\n\n"
        "👤 Встановити ім'я:\n"
        "`/setname <Ім'я Прізвище>`\n\n"
        "📅 Розклад на сьогодні:\n"
        "`/today`\n\n"
        "📅 Розклад на завтра:\n"
        "`/tomorrow`\n\n"
        "📋 Повний розклад:\n"
        "`/schedule`\n\n"
        "🔔 Керування сповіщеннями:\n"
        "`/notifications`\n\n"
        "💬 Комунікація:\n"
        "`/msg Ім'я повідомлення` - написати користувачу\n"
        "`/contact_headman` - зв'язатися зі старостою\n\n"
        "📚 Інформація:\n"
        "`/subjects` - список предметів\n"
        "`/subject Назва` - інформація про предмет\n"
        "`/teachers` - список викладачів\n\n"
        "ℹ️ Довідка:\n"
        "`/help` - всі команди"
    )

    if is_admin:
        welcome_text += (
            "\n\n👨‍💼 *Адмін-панель:*\nДоступні адмін-команди: `/admin_help`"
        )

    await message.answer(welcome_text, parse_mode="Markdown")
    logger.info(f"User {user_id} ({username}) started the bot")


@router.message(Command("help"))
@router.message(Command("commands"))
async def help_command(message: Message):
    """Handle /help and /commands commands."""
    user_id = message.from_user.id
    is_admin = user_id in settings.ADMIN_IDS

    help_text = (
        "📚 *Команди студентського бота СумДУ:*\n\n"
        "🏫 *Група:*\n"
        "`/setgroup <назва>` - встановити групу\n"
        "Приклад: `/setgroup КС-21`\n\n"
        "👤 *Профіль:*\n"
        "`/setname <Ім'я Прізвище>` - змінити ім'я\n\n"
        "📅 *Розклад:*\n"
        "`/today` - заняття на сьогодні\n"
        "`/tomorrow` - заняття на завтра\n"
        "`/schedule` - повний розклад\n\n"
        "🔔 *Сповіщення:*\n"
        "`/notifications` - увімкнути/вимкнути\n\n"
        "💬 *Комунікація:*\n"
        "`/msg Ім'я повідомлення` - написати\n"
        "`/contact_headman` - зв'язатися зі старостою\n"
        "`/messages` - мої повідомлення\n\n"
        "📚 *Навчання:*\n"
        "`/subjects` - всі предмети\n"
        "`/subject Назва` - про предмет\n"
        "`/teachers` - викладачі\n\n"
        "ℹ️ *Довідка:*\n"
        "`/help` - ця довідка"
    )

    if is_admin:
        help_text += "\n\n👨‍💼 *Адмін-команди:*\n`/admin_help` - адмін-панель"

    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("setname"))
async def set_name_command(message: Message):
    """Handle /setname command - set user's full name."""
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "❌ Будь ласка, вкажіть ім'я та прізвище!\nПриклад: `/setname Іван Іванов`",
            parse_mode="Markdown",
        )
        return

    full_name = args[1].strip()

    if len(full_name) < 3:
        await message.answer("❌ Ім'я занадто коротке!")
        return

    if len(full_name) > 100:
        await message.answer("❌ Ім'я занадто довге! Максимум 100 символів")
        return

    update_user_name(message.from_user.id, full_name)
    await message.answer(f"✅ Ім'я встановлено: *{full_name}*", parse_mode="Markdown")
    logger.info(f"User {message.from_user.id} set name to {full_name}")


@router.message(Command("setgroup"))
async def set_group_command(message: Message):
    """Handle /setgroup command - set user's group."""
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "❌ Будь ласка, вкажіть назву групи!\nПриклад: `/setgroup КС-21`",
            parse_mode="Markdown",
        )
        return

    group_name = args[1].strip().upper()

    if len(group_name) > 20:
        await message.answer("❌ Назва групи занадто довга! Максимум 20 символів")
        return

    if len(group_name) < 2:
        await message.answer("❌ Назва групи занадто коротка! Мінімум 2 символи")
        return

    update_user_group(message.from_user.id, group_name)
    await message.answer(f"✅ Групу встановлено: *{group_name}*", parse_mode="Markdown")
    logger.info(f"User {message.from_user.id} set group to {group_name}")


@router.message(Command("schedule"))
async def schedule_command(message: Message):
    """Handle /schedule command - show full schedule."""

    user = get_user(message.from_user.id)

    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`", parse_mode="Markdown"
        )
        return

    group_name = user["group_name"] if isinstance(user, dict) else user[1]

    if not group_name:
        await message.answer(
            "❌ Спочатку встановіть групу командою `/setgroup`", parse_mode="Markdown"
        )
        return

    # Get schedule from database
    events = get_events(group_name)

    if not events:
        await message.answer(
            f"📭 Для групи *{group_name}* немає запланованих подій у базі\n\n"
            "💡 Зверніться до адміністратора для завантаження розкладу",
            parse_mode="Markdown",
        )
        return

    # Convert to dict format
    events_dict = []
    for event in events:
        events_dict.append(
            {
                "date": event["date"] if isinstance(event, dict) else event[1],
                "time": event["time"] if isinstance(event, dict) else event[2],
                "title": event["title"] if isinstance(event, dict) else event[3],
                "room": event["room"] if isinstance(event, dict) else event[4],
                "group_name": event["group_name"]
                if isinstance(event, dict)
                else event[5],
                "lesson_type": event["lesson_type"]
                if isinstance(event, dict)
                else event[7],
            }
        )

    response = format_schedule_message(group_name, events_dict)
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("today"))
async def today_command(message: Message):
    """Handle /today command - show today's schedule."""
    from datetime import date

    user = get_user(message.from_user.id)

    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`", parse_mode="Markdown"
        )
        return

    group_name = user["group_name"] if isinstance(user, dict) else user[1]

    if not group_name:
        await message.answer(
            "❌ Спочатку встановіть групу командою `/setgroup`", parse_mode="Markdown"
        )
        return

    today = date.today().isoformat()
    today_formatted = date.today().strftime("%d.%m.%Y")

    # Get schedule from database
    events = get_events(group_name, today)

    if not events:
        await message.answer(
            f"📭 На *{today_formatted}* для *{group_name}* немає подій",
            parse_mode="Markdown",
        )
        return

    events_dict = []
    for event in events:
        events_dict.append(
            {
                "date": event["date"] if isinstance(event, dict) else event[1],
                "time": event["time"] if isinstance(event, dict) else event[2],
                "title": event["title"] if isinstance(event, dict) else event[3],
                "room": event["room"] if isinstance(event, dict) else event[4],
                "group_name": event["group_name"]
                if isinstance(event, dict)
                else event[5],
                "lesson_type": event["lesson_type"]
                if isinstance(event, dict)
                else event[7],
            }
        )

    response = format_schedule_message(group_name, events_dict, today_formatted)
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("notifications"))
async def notifications_command(message: Message):
    """Handle /notifications command - toggle notifications."""
    user = get_user(message.from_user.id)

    if not user:
        await message.answer("❌ Спочатку запустіть бота командою `/start`")
        return

    notifications_enabled = (
        user["notifications_enabled"] if isinstance(user, dict) else user[4]
    )
    new_status = not bool(notifications_enabled)

    toggle_notifications(message.from_user.id, new_status)

    status_text = "увімкнено" if new_status else "вимкнено"
    await message.answer(f"🔔 Сповіщення {status_text}!")
    logger.info(f"User {message.from_user.id} toggled notifications to {new_status}")


@router.message(Command("setrole"))
async def set_role_command(message: Message):
    """
    Allow users to set their own role (for teachers and group leaders).
    Format: /setrole teacher | group_leader
    """
    user_id = message.from_user.id

    # Only allow non-admin users to set limited roles
    if user_id in settings.ADMIN_IDS:
        await message.answer(
            "❌ Адміністратори не можуть змінювати свою роль цим способом",
            parse_mode="Markdown",
        )
        return

    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "❌ Вкажіть роль!\n\n"
            "Формат: `/setrole <роль>`\n\n"
            "Доступні ролі:\n"
            "• `teacher` - викладач\n"
            "• `group_leader` - староста\n\n"
            "💡 Примітка: Для призначення ролі іншим користувачам зверніться до адміністратора",
            parse_mode="Markdown",
        )
        return

    role_input = args[1].strip().lower()

    role_map = {
        "teacher": UserRole.TEACHER.value,
        "викладач": UserRole.TEACHER.value,
        "group_leader": UserRole.GROUP_LEADER.value,
        "староста": UserRole.GROUP_LEADER.value,
        "headman": UserRole.GROUP_LEADER.value,
    }

    if role_input not in role_map:
        await message.answer(
            "❌ Невідома роль!\n\n"
            "Доступні ролі:\n"
            "• `teacher` - викладач\n"
            "• `group_leader` - староста",
            parse_mode="Markdown",
        )
        return

    new_role = role_map[role_input]
    from database.models import update_user_role

    success = update_user_role(user_id, new_role)

    if success:
        role_names = {
            UserRole.TEACHER.value: "👨‍🏫 Викладач",
            UserRole.GROUP_LEADER.value: "👑 Староста",
        }
        await message.answer(
            f"✅ Ваша роль змінена на *{role_names.get(new_role, new_role)}*!",
            parse_mode="Markdown",
        )
        logger.info(f"User {user_id} self-assigned role {new_role}")
    else:
        await message.answer("❌ Помилка при зміні ролі")


# ============ Additional Commands ============


@router.message(Command("tomorrow"))
async def tomorrow_command(message: Message):
    """Handle /tomorrow command - show tomorrow's schedule."""
    from datetime import date, timedelta

    user = get_user(message.from_user.id)

    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`", parse_mode="Markdown"
        )
        return

    group_name = user["group_name"] if isinstance(user, dict) else user[1]

    if not group_name:
        await message.answer(
            "❌ Спочатку встановіть групу командою `/setgroup`", parse_mode="Markdown"
        )
        return

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    tomorrow_formatted = (date.today() + timedelta(days=1)).strftime("%d.%m.%Y")

    # Get schedule from database
    events = get_events(group_name, tomorrow)

    if not events:
        await message.answer(
            f"📭 На *{tomorrow_formatted}* для *{group_name}* немає подій",
            parse_mode="Markdown",
        )
        return

    events_dict = []
    for event in events:
        events_dict.append(
            {
                "date": event["date"] if isinstance(event, dict) else event[1],
                "time": event["time"] if isinstance(event, dict) else event[2],
                "title": event["title"] if isinstance(event, dict) else event[3],
                "room": event["room"] if isinstance(event, dict) else event[4],
                "group_name": event["group_name"]
                if isinstance(event, dict)
                else event[5],
                "lesson_type": event["lesson_type"]
                if isinstance(event, dict)
                else event[7],
            }
        )

    response = format_schedule_message(group_name, events_dict, "завтра")
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("teachers"))
async def teachers_command(message: Message):
    """Handle /teachers command - show list of teachers."""
    from database.models import get_all_teachers

    teachers = get_all_teachers()

    if not teachers:
        await message.answer(
            "📭 Викладачів поки що немає в базі", parse_mode="Markdown"
        )
        return

    response = "📚 *Викладачі:*\n\n"

    for teacher in teachers:
        name = teacher["full_name"] if isinstance(teacher, dict) else teacher[1]
        subject = teacher["subject"] if isinstance(teacher, dict) else teacher[2]
        email = teacher["email"] if isinstance(teacher, dict) else teacher[3]

        response += f"👨‍🏫 *{name}*\n"
        if subject:
            response += f"   📖 {subject}\n"
        if email:
            response += f"   📧 {email}\n"
        response += "\n"

    await message.answer(response, parse_mode="Markdown")

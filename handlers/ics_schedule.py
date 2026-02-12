"""
ICS Schedule Handlers - Робота з файлами розкладу .ics
Дозволяє завантажувати та парсити розклад з iCalendar файлів
"""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import settings
from database.models import add_event, get_events, delete_event, get_user
from services.ics_parser import ICSParser
from utils.decorators import admin_only

logger = logging.getLogger(__name__)

router = Router()


class ICSStates(StatesGroup):
    """FSM states for ICS file processing."""

    waiting_for_ics_file = State()


@router.message(Command("upload_ics"))
@admin_only
async def upload_ics_command(message: Message, state: FSMContext):
    """Handle /upload_ics command - upload iCalendar file."""
    await message.answer(
        "📤 *Завантаження розкладу з .ics файлу*\n\n"
        "Надішліть файл розкладу у форматі .ics\n"
        "(можна завантажити з кабінету студента)\n\n"
        "💡 *Як отримати файл:*\n"
        "1. Зайдіть в кабінет: cabinet.sumdu.edu.ua\n"
        "2. Перейдіть в розклад\n"
        "3. Натисніть 'Експорт' або 'Завантажити'\n"
        "4. Надішліть файл сюди",
        parse_mode="Markdown",
    )
    await state.set_state(ICSStates.waiting_for_ics_file)


@router.message(ICSStates.waiting_for_ics_file)
async def process_ics_file(message: Message, state: FSMContext):
    """Process uploaded .ics file."""
    if not message.document:
        await message.answer(
            "❌ Будь ласка, надішліть файл з розкладом", parse_mode="Markdown"
        )
        return

    document = message.document

    # Check file extension
    if not document.file_name.endswith(".ics"):
        await message.answer(
            "❌ Файл повинен мати розширення .ics", parse_mode="Markdown"
        )
        return

    try:
        # Download file
        file = await message.bot.get_file(document.file_id)
        file_content = await message.bot.download_file(file.file_path)
        ics_content = file_content.read().decode("utf-8")

        # Parse ICS content
        parser = ICSParser()
        events = parser.parse(ics_content)

        if not events:
            await message.answer(
                "❌ Не вдалося розпізнати події у файлі", parse_mode="Markdown"
            )
            await state.clear()
            return

        # Add events to database
        user_id = message.from_user.id
        user = get_user(user_id)
        group_name = user["group_name"] if user else None

        added_count = 0
        for event in events:
            try:
                # Parse date and time
                date_str = event.dtstart.strftime("%Y-%m-%d")
                time_str = event.dtstart.strftime("%H:%M")

                # Determine lesson type from summary
                lesson_type = "lecture"
                summary_lower = event.summary.lower()
                if "лаборатор" in summary_lower:
                    lesson_type = "laboratory"
                elif "практичн" in summary_lower:
                    lesson_type = "practice"

                add_event(
                    date=date_str,
                    time=time_str,
                    title=event.summary,
                    room=event.location or "Ауд. не вказано",
                    group_name=group_name or "DEFAULT",
                    lesson_type=lesson_type,
                )
                added_count += 1
            except Exception as e:
                logger.error(f"Error adding event: {e}")
                continue

        # Format for display
        formatted_schedule = parser.format_for_display(events[:10])  # First 10 events

        response = (
            f"✅ *Розклад завантажено!*\n\n"
            f"📊 Знайдено подій: {len(events)}\n"
            f"💾 Додано до бази: {added_count}\n\n"
            f"{formatted_schedule}"
        )

        await message.answer(response[:4000], parse_mode="Markdown")
        await state.clear()

        logger.info(f"User {user_id} uploaded {len(events)} events from ICS file")

    except Exception as e:
        logger.error(f"Error processing ICS file: {e}")
        await message.answer(
            f"❌ Помилка при обробці файлу: {e}", parse_mode="Markdown"
        )
        await state.clear()


@router.message(Command("tomorrow"))
async def tomorrow_schedule_command(message: Message):
    """Handle /tomorrow command - show tomorrow's schedule."""
    from datetime import date, timedelta

    user = get_user(message.from_user.id)
    group_name = user["group_name"] if user else None

    if not group_name:
        await message.answer(
            "❌ Спочатку встановіть групу командою `/setgroup`", parse_mode="Markdown"
        )
        return

    tomorrow = date.today() + timedelta(days=1)
    tomorrow_str = tomorrow.isoformat()
    tomorrow_formatted = tomorrow.strftime("%d.%m.%Y")

    # Get events from database
    events = get_events(group_name, tomorrow_str)

    if not events:
        await message.answer(
            f"📭 На *{tomorrow_formatted}* для *{group_name}* немає запланованих занять",
            parse_mode="Markdown",
        )
        return

    response = f"📅 *Розклад на завтра ({tomorrow_formatted})*\n\n"

    for event in events:
        event_time = event["time"] if isinstance(event, dict) else event[2]
        event_title = event["title"] if isinstance(event, dict) else event[3]
        event_room = event["room"] if isinstance(event, dict) else event[4]

        lesson_type = event["lesson_type"] if isinstance(event, dict) else event[7]
        emoji = {"lecture": "📚", "practice": "✍️", "laboratory": "🔬"}.get(
            lesson_type, "📚"
        )

        response += f"{emoji} *{event_time}*\n"
        response += f"   📖 {event_title}\n"
        response += f"   📍 {event_room}\n\n"

    await message.answer(response, parse_mode="Markdown")


@router.message(Command("schedule_week"))
async def week_schedule_command(message: Message):
    """Handle /schedule_week command - show this week's schedule."""
    from datetime import date, timedelta

    user = get_user(message.from_user.id)
    group_name = user["group_name"] if user else None

    if not group_name:
        await message.answer(
            "❌ Спочатку встановіть групу командою `/setgroup`", parse_mode="Markdown"
        )
        return

    # Get all events
    events = get_events(group_name)

    if not events:
        await message.answer(
            f"📭 Для *{group_name}* немає запланованих занять", parse_mode="Markdown"
        )
        return

    # Filter events for this week
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    week_events = []
    for event in events:
        event_date = event["date"] if isinstance(event, dict) else event[1]
        if week_start.isoformat() <= event_date <= week_end.isoformat():
            week_events.append(event)

    if not week_events:
        await message.answer(
            f"📭 На цьому тижні для *{group_name}* немає занять", parse_mode="Markdown"
        )
        return

    response = f"📅 *Розклад на тиждень ({week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m.%Y')})*\n\n"

    # Group by date
    by_date = {}
    for event in week_events:
        event_date = event["date"] if isinstance(event, dict) else event[1]
        if event_date not in by_date:
            by_date[event_date] = []
        by_date[event_date].append(event)

    # Format
    for date_key in sorted(by_date.keys()):
        date_obj = date.fromisoformat(date_key)
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"][date_obj.weekday()]
        date_formatted = date_obj.strftime(f"%d.%m ({day_name})")

        response += f"📆 *{date_formatted}:*\n"

        for event in by_date[date_key]:
            event_time = event["time"] if isinstance(event, dict) else event[2]
            event_title = event["title"] if isinstance(event, dict) else event[3]
            event_room = event["room"] if isinstance(event, dict) else event[4]

            lesson_type = event["lesson_type"] if isinstance(event, dict) else event[7]
            emoji = {"lecture": "📚", "practice": "✍️", "laboratory": "🔬"}.get(
                lesson_type, "📚"
            )

            response += f"{emoji} {event_time} - {event_title} ({event_room})\n"

        response += "\n"

    # Split if too long
    if len(response) > 4000:
        parts = [response[i : i + 4000] for i in range(0, len(response), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="Markdown")
    else:
        await message.answer(response, parse_mode="Markdown")


@router.message(Command("clear_schedule"))
async def clear_schedule_command(message: Message):
    """Handle /clear_schedule command - clear all schedule events."""
    from database.models import get_all_events

    user_id = message.from_user.id

    if user_id not in settings.ADMIN_IDS:
        await message.answer(
            "❌ Ця команда доступна лише адміністраторам", parse_mode="Markdown"
        )
        return

    # Delete all events
    events = get_all_events()
    count = len(events)

    for event in events:
        event_id = event["id"] if isinstance(event, dict) else event[0]
        delete_event(event_id)

    await message.answer(
        f"✅ Розклад очищено!\n\nВидалено подій: {count}", parse_mode="Markdown"
    )

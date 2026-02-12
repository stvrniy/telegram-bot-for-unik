"""
Teacher command handlers for the Telegram Education Bot.
Allows teachers to manually edit their schedule items.
"""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database.models import (
    get_user, get_events, edit_event, delete_event,
    get_teacher_subjects, UserRole
)
from utils.decorators import validate_date, validate_time

logger = logging.getLogger(__name__)

router = Router()


class TeacherEditStates(StatesGroup):
    """FSM states for teacher schedule editing."""
    waiting_for_event_id = State()
    waiting_for_new_date = State()
    waiting_for_new_time = State()
    waiting_for_new_title = State()
    waiting_for_new_room = State()
    waiting_for_confirmation = State()


@router.message(Command("teacher_help"))
async def teacher_help_command(message: Message):
    """Handle /teacher_help command - show teacher commands."""
    help_text = (
        "👨‍🏫 *Команди викладача:*\n\n"
        "📝 *Редагування розкладу:*\n"
        "`/my_schedule` - показати мій розклад\n"
        "`/edit_lesson` - редагувати заняття\n"
        "`/delete_lesson <id>` - видалити заняття\n\n"
        "📋 *Мої предмети:*\n"
        "`/my_subjects` - показати мої предмети\n\n"
        "ℹ️ *Довідка:*\n"
        "`/teacher_help` - ця довідка"
    )
    
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("my_schedule"))
async def my_schedule_command(message: Message):
    """Handle /my_schedule command - show teacher's schedule."""
    user = get_user(message.from_user.id)
    
    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`",
            parse_mode="Markdown"
        )
        return
    
    user_id = message.from_user.id
    
    # Check if user is a teacher
    if user['role'] != UserRole.TEACHER.value:
        await message.answer(
            "❌ Ця команда доступна лише викладачам.\n"
            "Зверніться до адміністратора для призначення ролі викладача.",
            parse_mode="Markdown"
        )
        return
    
    # Get teacher's subjects
    teacher_subjects = get_teacher_subjects(user_id)
    
    if not teacher_subjects:
        await message.answer(
            "📭 У вас немає призначених предметів.\n"
            "Зверніться до адміністратора для налаштування.",
            parse_mode="Markdown"
        )
        return
    
    # Get all events for teacher's subjects
    all_events = []
    for ts in teacher_subjects:
        subject_name = ts['subject_name'] if isinstance(ts, dict) else ts[2]
        group_name = ts['group_name'] if isinstance(ts, dict) else ts[3]
        events = get_events(group_name)
        for event in events:
            event_title = event['title'] if isinstance(event, dict) else event[3]
            if subject_name.lower() in event_title.lower():
                all_events.append({
                    'event': event,
                    'group': group_name,
                    'subject': subject_name
                })
    
    if not all_events:
        await message.answer(
            "📭 У вас немає запланованих занять",
            parse_mode="Markdown"
        )
        return
    
    response = "📅 *Ваш розклад:*\n\n"
    
    # Group by group
    by_group = {}
    for item in all_events:
        group = item['group']
        if group not in by_group:
            by_group[group] = []
        by_group[group].append(item)
    
    for group in sorted(by_group.keys()):
        response += f"🏫 *Група {group}:*\\n"
        for item in by_group[group]:
            event = item['event']
            event_id = event['id'] if isinstance(event, dict) else event[0]
            event_date = event['date'] if isinstance(event, dict) else event[1]
            event_time = event['time'] if isinstance(event, dict) else event[2]
            event_title = event['title'] if isinstance(event, dict) else event[3]
            event_room = event['room'] if isinstance(event, dict) else event[4]
            
            response += f"🆔 `{event_id}` | {event_date} {event_time}\\n"
            response += f"   📖 {event_title}\\n"
            response += f"   📍 {event_room}\\n\\n"
    
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("my_subjects"))
async def my_subjects_command(message: Message):
    """Handle /my_subjects command - show teacher's subjects."""
    user = get_user(message.from_user.id)
    
    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`",
            parse_mode="Markdown"
        )
        return
    
    user_id = message.from_user.id
    
    # Check if user is a teacher
    if user['role'] != UserRole.TEACHER.value:
        await message.answer(
            "❌ Ця команда доступна лише викладачам",
            parse_mode="Markdown"
        )
        return
    
    teacher_subjects = get_teacher_subjects(user_id)
    
    if not teacher_subjects:
        await message.answer(
            "📭 У вас немає призначених предметів",
            parse_mode="Markdown"
        )
        return
    
    response = "📚 *Ваші предмети:*\\n\\n"
    
    for ts in teacher_subjects:
        subject_name = ts['subject_name'] if isinstance(ts, dict) else ts[2]
        group_name = ts['group_name'] if isinstance(ts, dict) else ts[3]
        response += f"📖 {subject_name}\\n"
        response += f"   🏫 Група: {group_name}\\n\\n"
    
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("edit_lesson"))
async def edit_lesson_command(message: Message, state: FSMContext):
    """Start the process of editing a lesson."""
    user = get_user(message.from_user.id)
    
    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`",
            parse_mode="Markdown"
        )
        return
    
    # Check if user is a teacher
    if user['role'] != UserRole.TEACHER.value:
        await message.answer(
            "❌ Ця команда доступна лише викладачам",
            parse_mode="Markdown"
        )
        return
    
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "📝 *Редагування заняття*\\n\\n"
            "Введіть ID заняття, яке хочете редагувати:",
            parse_mode="Markdown"
        )
        await state.set_state(TeacherEditStates.waiting_for_event_id)
        return
    
    event_id = args[1].strip()
    
    # Validate event exists
    all_events = get_events(None)  # Get all events
    event = None
    for e in all_events:
        e_id = str(e['id'] if isinstance(e, dict) else e[0])
        if e_id == event_id:
            event = e
            break
    
    if not event:
        await message.answer(
            f"❌ Заняття з ID `{event_id}` не знайдено",
            parse_mode="Markdown"
        )
        return
    
    # Store event ID and ask for new date
    await state.update_data(event_id=event_id)
    
    event_date = event['date'] if isinstance(event, dict) else event[1]
    event_time = event['time'] if isinstance(event, dict) else event[2]
    event_title = event['title'] if isinstance(event, dict) else event[3]
    event_room = event['room'] if isinstance(event, dict) else event[4]
    
    await message.answer(
        f"📝 *Редагування заняття (ID: {event_id})*\\n\\n"
        f"📅 Поточна дата: `{event_date}`\\n"
        f"⏰ Поточний час: `{event_time}`\\n"
        f"📖 Поточна назва: `{event_title}`\\n"
        f"📍 Поточна аудиторія: `{event_room}`\\n\\n"
        "Введіть нову дату у форматі YYYY-MM-DD (або `-` щоб залишити без змін):",
        parse_mode="Markdown"
    )
    await state.set_state(TeacherEditStates.waiting_for_new_date)


@router.message(TeacherEditStates.waiting_for_event_id)
async def process_event_id(message: Message, state: FSMContext):
    """Process event ID input."""
    event_id = message.text.strip()
    
    # Get all events
    all_events = get_events(None)
    event = None
    for e in all_events:
        e_id = str(e['id'] if isinstance(e, dict) else e[0])
        if e_id == event_id:
            event = e
            break
    
    if not event:
        await message.answer(
            f"❌ Заняття з ID `{event_id}` не знайдено. Спробуйте ще раз:",
            parse_mode="Markdown"
        )
        return
    
    await state.update_data(event_id=event_id)
    
    event_date = event['date'] if isinstance(event, dict) else event[1]
    event_time = event['time'] if isinstance(event, dict) else event[2]
    event_title = event['title'] if isinstance(event, dict) else event[3]
    event_room = event['room'] if isinstance(event, dict) else event[4]
    
    await message.answer(
        f"📝 *Редагування заняття (ID: {event_id})*\\n\\n"
        f"📅 Поточна дата: `{event_date}`\\n"
        f"⏰ Поточний час: `{event_time}`\\n"
        f"📖 Поточна назва: `{event_title}`\\n"
        f"📍 Поточна аудиторія: `{event_room}`\\n\\n"
        "Введіть нову дату у форматі YYYY-MM-DD (або `-` щоб залишити без змін):",
        parse_mode="Markdown"
    )
    await state.set_state(TeacherEditStates.waiting_for_new_date)


@router.message(TeacherEditStates.waiting_for_new_date)
async def process_new_date(message: Message, state: FSMContext):
    """Process new date input."""
    date_input = message.text.strip()
    
    if date_input == '-':
        # Get current event data to keep date
        data = await state.get_data()
        event_id = data.get('event_id')
        all_events = get_events(None)
        for e in all_events:
            e_id = str(e['id'] if isinstance(e, dict) else e[0])
            if e_id == event_id:
                event = e
                date_input = event['date'] if isinstance(event, dict) else event[1]
                break
    
    if date_input != '-' and not validate_date(date_input):
        await message.answer(
            "❌ Неправильний формат дати! Використовуйте YYYY-MM-DD",
            parse_mode="Markdown"
        )
        return
    
    await state.update_data(new_date=date_input if date_input != '-' else None)
    
    await message.answer(
        "Введіть новий час у форматі HH:MM (або `-` щоб залишити без змін):",
        parse_mode="Markdown"
    )
    await state.set_state(TeacherEditStates.waiting_for_new_time)


@router.message(TeacherEditStates.waiting_for_new_time)
async def process_new_time(message: Message, state: FSMContext):
    """Process new time input."""
    time_input = message.text.strip()
    
    if time_input == '-':
        # Get current event data to keep time
        data = await state.get_data()
        event_id = data.get('event_id')
        all_events = get_events(None)
        for e in all_events:
            e_id = str(e['id'] if isinstance(e, dict) else e[0])
            if e_id == event_id:
                event = e
                time_input = event['time'] if isinstance(event, dict) else event[2]
                break
    
    if time_input != '-' and not validate_time(time_input):
        await message.answer(
            "❌ Неправильний формат часу! Використовуйте HH:MM",
            parse_mode="Markdown"
        )
        return
    
    await state.update_data(new_time=time_input if time_input != '-' else None)
    
    await message.answer(
        "Введіть нову назву заняття (або `-` щоб залишити без змін):",
        parse_mode="Markdown"
    )
    await state.set_state(TeacherEditStates.waiting_for_new_title)


@router.message(TeacherEditStates.waiting_for_new_title)
async def process_new_title(message: Message, state: FSMContext):
    """Process new title input."""
    title_input = message.text.strip()
    
    if title_input == '-':
        # Get current event data to keep title
        data = await state.get_data()
        event_id = data.get('event_id')
        all_events = get_events(None)
        for e in all_events:
            e_id = str(e['id'] if isinstance(e, dict) else e[0])
            if e_id == event_id:
                event = e
                title_input = event['title'] if isinstance(event, dict) else event[3]
                break
    
    await state.update_data(new_title=title_input if title_input != '-' else None)
    
    await message.answer(
        "Введіть нову аудиторію (або `-` щоб залишити без змін):",
        parse_mode="Markdown"
    )
    await state.set_state(TeacherEditStates.waiting_for_new_room)


@router.message(TeacherEditStates.waiting_for_new_room)
async def process_new_room(message: Message, state: FSMContext):
    """Process new room input."""
    room_input = message.text.strip()
    
    if room_input == '-':
        # Get current event data to keep room
        data = await state.get_data()
        event_id = data.get('event_id')
        all_events = get_events(None)
        for e in all_events:
            e_id = str(e['id'] if isinstance(e, dict) else e[0])
            if e_id == event_id:
                event = e
                room_input = event['room'] if isinstance(event, dict) else event[4]
                break
    
    # Get all current data
    data = await state.get_data()
    event_id = data.get('event_id')
    new_date = data.get('new_date')
    new_time = data.get('new_time')
    new_title = data.get('new_title')
    
    # Get current event data
    all_events = get_events(None)
    event = None
    for e in all_events:
        e_id = str(e['id'] if isinstance(e, dict) else e[0])
        if e_id == event_id:
            event = e
            break
    
    if not event:
        await message.answer("❌ Помилка: заняття не знайдено")
        await state.clear()
        return
    
    # Apply changes (use current values if not changed)
    final_date = new_date if new_date else (event['date'] if isinstance(event, dict) else event[1])
    final_time = new_time if new_time else (event['time'] if isinstance(event, dict) else event[2])
    final_title = new_title if new_title else (event['title'] if isinstance(event, dict) else event[3])
    final_room = room_input if room_input != '-' else (event['room'] if isinstance(event, dict) else event[4])
    
    # Confirm changes
    await message.answer(
        f"📝 *Підтвердіть зміни:*\\n\\n"
        f"🆔 ID заняття: `{event_id}`\\n"
        f"📅 Нова дата: `{final_date}`\\n"
        f"⏰ Новий час: `{final_time}`\\n"
        f"📖 Нова назва: `{final_title}`\\n"
        f"📍 Нова аудиторія: `{final_room}`\\n\\n"
        "Введіть `+` для підтвердження або `-` для скасування:",
        parse_mode="Markdown"
    )
    
    await state.update_data(
        final_date=final_date,
        final_time=final_time,
        final_title=final_title,
        final_room=final_room
    )
    await state.set_state(TeacherEditStates.waiting_for_confirmation)


@router.message(TeacherEditStates.waiting_for_confirmation)
async def process_confirmation(message: Message, state: FSMContext):
    """Process confirmation for edit."""
    confirmation = message.text.strip().lower()
    
    if confirmation != '+':
        await message.answer("❌ Редагування скасовано", parse_mode="Markdown")
        await state.clear()
        return
    
    data = await state.get_data()
    event_id = int(data.get('event_id'))
    final_date = data.get('final_date')
    final_time = data.get('final_time')
    final_title = data.get('final_title')
    final_room = data.get('final_room')
    
    # Get current event to preserve group_name and teacher_id
    all_events = get_events(None)
    event = None
    for e in all_events:
        e_id = e['id'] if isinstance(e, dict) else e[0]
        if e_id == event_id:
            event = e
            break
    
    if not event:
        await message.answer("❌ Помилка: заняття не знайдено")
        await state.clear()
        return
    
    group_name = event['group_name'] if isinstance(event, dict) else event[5]
    teacher_id = event.get('teacher_id')
    lesson_type = event.get('lesson_type', 'lecture')
    
    # Update the event
    success = edit_event(
        event_id=event_id,
        date=final_date,
        time=final_time,
        title=final_title,
        room=final_room,
        group_name=group_name,
        teacher_id=teacher_id,
        lesson_type=lesson_type
    )
    
    if success:
        await message.answer(
            f"✅ Заняття успішно оновлено!\\n\\n"
            f"📅 {final_date} о {final_time}\\n"
            f"📖 {final_title}\\n"
            f"📍 {final_room}",
            parse_mode="Markdown"
        )
        logger.info(f"Teacher edited event {event_id}")
    else:
        await message.answer("❌ Помилка при оновленні заняття", parse_mode="Markdown")
    
    await state.clear()


@router.message(Command("delete_lesson"))
async def delete_lesson_command(message: Message):
    """Handle /delete_lesson command - delete a lesson."""
    user = get_user(message.from_user.id)
    
    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`",
            parse_mode="Markdown"
        )
        return
    
    # Check if user is a teacher
    if user['role'] != UserRole.TEACHER.value:
        await message.answer(
            "❌ Ця команда доступна лише викладачам",
            parse_mode="Markdown"
        )
        return
    
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "❌ Вкажіть ID заняття!\\n"
            "Формат: `/delete_lesson <id>`\\n"
            "Приклад: `/delete_lesson 5`",
            parse_mode="Markdown"
        )
        return
    
    try:
        event_id = int(args[1].strip())
    except ValueError:
        await message.answer(
            "❌ Невірний формат ID! ID повинно бути числом",
            parse_mode="Markdown"
        )
        return
    
    success = delete_event(event_id)
    
    if success:
        await message.answer(
            f"✅ Заняття з ID `{event_id}` видалено",
            parse_mode="Markdown"
        )
        logger.info(f"Teacher deleted event {event_id}")
    else:
        await message.answer(
            f"❌ Заняття з ID `{event_id}` не знайдено",
            parse_mode="Markdown"
        )

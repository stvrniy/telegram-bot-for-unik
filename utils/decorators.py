"""
Shared decorators and utilities for the Telegram Education Bot.
"""

from functools import wraps
from typing import Callable, Any, List, Optional
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from config.settings import settings
from database.models import UserRole


def admin_only(func: Callable) -> Callable:
    """
    Decorator to restrict commands to admins only.
    Must be used with aiogram handlers.
    """
    @wraps(func)
    async def wrapper(message: Message, *args: Any, **kwargs: Any) -> Any:
        user_id = message.from_user.id
        if user_id not in settings.ADMIN_IDS:
            await message.answer(
                "❌ Ця команда доступна лише адміністраторам",
                parse_mode="Markdown"
            )
            return
        return await func(message, *args, **kwargs)
    return wrapper


def role_required(allowed_roles: List[str]) -> Callable:
    """
    Decorator to restrict commands to specific roles.
    
    Args:
        allowed_roles: List of allowed role names (student, group_leader, teacher, admin)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(message: Message, *args: Any, **kwargs: Any) -> Any:
            from database.models import get_user
            
            user_id = message.from_user.id
            user = get_user(user_id)
            
            if not user:
                await message.answer(
                    "❌ Спочатку запустіть бота командою `/start`",
                    parse_mode="Markdown"
                )
                return
            
            user_role = user['role'] if isinstance(user, dict) else user[3]
            
            if user_role not in allowed_roles and user_id not in settings.ADMIN_IDS:
                role_names = {
                    'student': 'студентів',
                    'group_leader': 'старост',
                    'teacher': 'викладачів',
                    'admin': 'адміністраторів'
                }
                roles_text = ', '.join([role_names.get(r, r) for r in allowed_roles])
                await message.answer(
                    f"❌ Ця команда доступна лише для {roles_text}",
                    parse_mode="Markdown"
                )
                return
            
            return await func(message, *args, **kwargs)
        return wrapper
    return decorator


def extract_command_args(text: str, command: str) -> list:
    """
    Extract arguments from a command message.
    
    Args:
        text: Full message text
        command: Command name (e.g., '/add_event')
    
    Returns:
        List of arguments
    """
    if not text.startswith(command):
        return []
    
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return []
    
    args_part = parts[1].strip()
    return args_part.split() if args_part else []


def format_event_message(event: dict) -> str:
    """
    Format an event dict into a readable message.
    """
    lesson_emoji = {
        'lecture': '📚',
        'practice': '✍️',
        'laboratory': '🔬',
        'exam': '📝',
        'consultation': '💬'
    }.get(event.get('lesson_type', 'lecture'), '📚')
    
    return (
        f"{lesson_emoji} *{event.get('title', 'Без назви')}*\n"
        f"⏰ {event.get('time', '')} | 📅 {event.get('date', '')}\n"
        f"🏫 Ауд. {event.get('room', 'Невідома')} | 👥 {event.get('group_name', '')}\n"
        f"📖 Тип: {event.get('lesson_type', 'лекція')}"
    )


def format_schedule_message(
    group_name: str, 
    events: list, 
    date_info: str = ""
) -> str:
    """
    Format a list of events into a readable schedule message.
    
    Args:
        group_name: Name of the group
        events: List of event dicts
        date_info: Optional date info (e.g., "сьогодні", "завтра")
    
    Returns:
        Formatted schedule message
    """
    if date_info:
        response = f"📅 *Розклад на {date_info} для {group_name}:*\n\n"
    else:
        response = f"📋 *Розклад для {group_name}:*\n\n"
    
    if not events:
        response += "📭 Немає запланованих занять"
        return response
    
    current_date = None
    for event in events:
        event_date = event.get('date', '')
        
        if event_date != current_date and not date_info:
            current_date = event_date
            response += f"\n📆 *{event_date}:*\n"
        
        event_time = event.get('time', '')
        event_title = event.get('title', '')
        event_room = event.get('room', '')
        lesson_type = event.get('lesson_type', 'lecture')
        
        lesson_emoji = {
            'lecture': '📚',
            'practice': '✍️',
            'laboratory': '🔬'
        }.get(lesson_type, '📚')
        
        response += f"{lesson_emoji} {event_time}: {event_title} (ауд. {event_room})\n"
    
    return response


def validate_date(date_str: str, date_format: str = "%Y-%m-%d") -> bool:
    """Validate date string format."""
    try:
        from datetime import datetime
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False


def validate_time(time_str: str, time_format: str = "%H:%M") -> bool:
    """Validate time string format."""
    try:
        from datetime import datetime
        datetime.strptime(time_str, time_format)
        return True
    except ValueError:
        return False


def format_subject_info(subject_info: dict) -> str:
    """
    Format subject information into a readable message.
    
    Args:
        subject_info: Dict with subject details
        
    Returns:
        Formatted subject info message
    """
    response = (
        f"📖 *{subject_info.get('name', 'Невідомий предмет')}*\n\n"
        f"🏷️ Скорочення: `{subject_info.get('short_name', '—')}`\n"
        f"📊 Кредити: *{subject_info.get('credits', 0)}*\n\n"
        f"📝 *Опис:*\n{subject_info.get('description', 'Опис відсутній')}\n"
    )
    
    topics = subject_info.get('topics', [])
    if topics:
        response += f"\n📚 *Теми курсу:*\n"
        for i, topic in enumerate(topics, 1):
            response += f"{i}. {topic}\n"
    
    return response

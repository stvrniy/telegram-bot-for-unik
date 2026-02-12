"""
Communication handlers for the Telegram Education Bot.
Handles user-to-user messaging, including students with teachers and group leaders.
"""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import (
    get_user, get_users_by_name, send_message, 
    get_messages, get_unread_count,
    get_group_leader, get_all_subjects, get_group_subjects, add_group_subject
)
from utils.decorators import role_required

logger = logging.getLogger(__name__)

router = Router()


class MessageStates(StatesGroup):
    """FSM states for messaging workflow."""
    waiting_for_recipient = State()
    waiting_for_message = State()


class BroadcastStates(StatesGroup):
    """FSM states for broadcasting messages."""
    waiting_for_message = State()


@router.message(Command("messages"))
@router.message(Command("inbox"))
async def messages_command(message: Message):
    """Handle /messages command - show user's messages."""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`",
            parse_mode="Markdown"
        )
        return
    
    unread_count = get_unread_count(user_id)
    messages_list = get_messages(user_id, unread_only=False)
    
    # Header with unread count
    if unread_count > 0:
        header = f"📬 *Ваші повідомлення* (непрочитаних: {unread_count}):\n\n"
    else:
        header = "📬 *Ваші повідомлення:*\n\n"
    
    if not messages_list:
        await message.answer(
            header + "📭 У вас немає повідомлень",
            parse_mode="Markdown"
        )
        return
    
    response = header
    
    # Group messages by sender
    by_sender = {}
    for msg in messages_list:
        sender_name = msg['sender_name'] or "Невідомий"
        if sender_name not in by_sender:
            by_sender[sender_name] = []
        by_sender[sender_name].append(msg)
    
    for sender_name, msgs in by_sender.items():
        latest_msg = msgs[0]
        is_unread = latest_msg['is_read'] == 0
        
        response += f"{'🔵' if is_unread else '⚪'} *{sender_name}*\n"
        response += f"   {latest_msg['message'][:50]}"
        if len(latest_msg['message']) > 50:
            response += "..."
        response += f"\n   _{latest_msg['created_at'][:16]}_\n\n"
    
    # Show unread first
    unread_msgs = [m for m in messages_list if m['is_read'] == 0]
    if unread_msgs:
        response += "\n---\n\n*Непрочитані повідомлення:*\n"
        for msg in unread_msgs[:5]:  # Show last 5 unread
            sender_name = msg['sender_name'] or "Невідомий"
            response += f"\n📩 *{sender_name}:*\n"
            response += f"_{msg['created_at'][:16]}_\n"
            response += f"{msg['message']}\n"
            
            # Add mark as read button
            await message.bot.send_message(
                user_id,
                f"📩 Від: *{sender_name}*\n\n{msg['message']}\n\n__{msg['created_at']}__",
                parse_mode="Markdown"
            )
    
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("unread"))
async def unread_command(message: Message):
    """Handle /unread command - show only unread messages."""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`",
            parse_mode="Markdown"
        )
        return
    
    unread_count = get_unread_count(user_id)
    
    if unread_count == 0:
        await message.answer(
            "✅ У вас немає непрочитаних повідомлень",
            parse_mode="Markdown"
        )
        return
    
    messages_list = get_messages(user_id, unread_only=True)
    
    response = f"📬 *Непрочитані повідомлення ({unread_count}):*\n\n"
    
    for msg in messages_list:
        sender_name = msg['sender_name'] or "Невідомий"
        response += f"📩 *{sender_name}*\n"
        response += f"_{msg['created_at'][:16]}_\n"
        response += f"{msg['message']}\n\n"
    
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("msg"))
async def msg_command(message: Message):
    """
    Handle /msg command - send a message to another user.
    Format: /msg Ім'я Прізвище Ваше повідомлення
    """
    args = message.text.split(maxsplit=2)
    
    if len(args) < 3:
        await message.answer(
            "❌ Неправильний формат!\n"
            "Формат: `/msg Ім'я Прізвище Ваше повідомлення`\n\n"
            "Приклад: `/msg Іван Іванов Питання щодо розкладу`",
            parse_mode="Markdown"
        )
        return
    
    recipient_name = args[1]
    text = args[2]
    
    # Search for recipient
    recipients = get_users_by_name(recipient_name)
    
    if not recipients:
        await message.answer(
            f"❌ Користувача '{recipient_name}' не знайдено",
            parse_mode="Markdown"
        )
        return
    
    if len(recipients) > 1:
        # Multiple matches - ask for clarification
        response = (
            f"❌ Знайдено кілька користувачів з ім'ям '{recipient_name}':\n\n"
        )
        for i, r in enumerate(recipients, 1):
            user_role = r['role'] if isinstance(r, dict) else r[3]
            role_names = {
                'student': 'студент',
                'group_leader': 'старсота',
                'teacher': 'викладач',
                'admin': 'адмін'
            }
            role_text = role_names.get(user_role, user_role)
            group = r['group_name'] if isinstance(r, dict) else r[1]
            response += f"{i}. {r['full_name']} ({role_text}) - {group}\n"
        
        response += "\nВкажіть повніше ім'я або ID"
        await message.answer(response, parse_mode="Markdown")
        return
    
    # Send to single recipient
    recipient = recipients[0]
    recipient_id = recipient['user_id'] if isinstance(recipient, dict) else recipient[0]
    
    sender_id = message.from_user.id
    sender = get_user(sender_id)
    sender_name = sender['full_name'] if isinstance(sender, dict) else sender[2]
    
    # Send message to recipient
    message_text = (
        f"📩 *Нове повідомлення від {sender_name}:*\n\n"
        f"{text}"
    )
    
    try:
        await message.bot.send_message(recipient_id, message_text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(
            f"❌ Не вдалося відправити повідомлення: {e}",
            parse_mode="Markdown"
        )
        return
    
    # Store message in database
    send_message(sender_id, recipient_id, text)
    
    await message.answer(
        f"✅ Повідомлення відправлено {sender_name}!",
        parse_mode="Markdown"
    )
    logger.info(f"Message sent from {sender_id} to {recipient_id}")


@router.message(Command("contact_group_leader"))
@router.message(Command("contact_headman"))
async def contact_group_leader_command(message: Message):
    """Handle /contact_group_leader - send message to group leader."""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`",
            parse_mode="Markdown"
        )
        return
    
    group_name = user['group_name'] if isinstance(user, dict) else user[1]
    
    if not group_name:
        await message.answer(
            "❌ Спочатку встановіть групу командою `/setgroup`",
            parse_mode="Markdown"
        )
        return
    
    group_leader = get_group_leader(group_name)
    
    if not group_leader:
        await message.answer(
            f"❌ У групі {group_name} не призначено старосту.\n"
            "Зверніться до адміністратора для призначення.",
            parse_mode="Markdown"
        )
        return
    
    leader_name = group_leader['full_name'] if isinstance(group_leader, dict) else group_leader[2]
    
    await message.answer(
        f"👤 *Староста групи {group_name}:* {leader_name}\n\n"
        "Введіть ваше повідомлення для нього/неї:",
        parse_mode="Markdown"
    )
    await message.state.set_state(MessageStates.waiting_for_recipient)


@router.message(MessageStates.waiting_for_recipient)
async def process_recipient_selection(message: Message, state: FSMContext):
    """Process message recipient after user selects to message group leader."""
    user_id = message.from_user.id
    user = get_user(user_id)
    group_name = user['group_name'] if isinstance(user, dict) else user[1]
    
    group_leader = get_group_leader(group_name)
    
    if not group_leader:
        await message.answer("❌ Помилка: старосту не знайдено")
        await state.clear()
        return
    
    leader_id = group_leader['user_id'] if isinstance(group_leader, dict) else group_leader[0]
    
    await state.update_data(recipient_id=leader_id)
    await message.answer("💬 Введіть ваше повідомлення:")
    await state.set_state(MessageStates.waiting_for_message)


@router.message(MessageStates.waiting_for_message)
async def process_message_to_recipient(message: Message, state: FSMContext):
    """Send the message to the selected recipient."""
    if not message.text:
        await message.answer("❌ Повідомлення повинно містити текст")
        return
    
    data = await state.get_data()
    recipient_id = data.get('recipient_id')
    
    if not recipient_id:
        await message.answer("❌ Помилка: отримувач не вибраний")
        await state.clear()
        return
    
    sender_id = message.from_user.id
    sender = get_user(sender_id)
    sender_name = sender['full_name'] if isinstance(sender, dict) else sender[2]
    
    # Send message
    message_text = (
        f"📩 *Повідомлення від {sender_name}:*\n\n"
        f"{message.text}"
    )
    
    try:
        await message.bot.send_message(recipient_id, message_text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(
            f"❌ Не вдалося відправити повідомлення: {e}",
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    # Store message
    send_message(sender_id, recipient_id, message.text)
    
    await message.answer("✅ Повідомлення відправлено!", parse_mode="Markdown")
    await state.clear()
    logger.info(f"Message sent from {sender_id} to {recipient_id}")


@router.message(Command("subjects"))
async def subjects_command(message: Message):
    """Handle /subjects command - show list of subjects."""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # Get user's group if available
    group_name = None
    if user:
        group_name = user['group_name'] if isinstance(user, dict) else user[1]
    
    # Show subjects for user's group if available
    if group_name:
        group_subjects = get_group_subjects(group_name)
        if group_subjects:
            response = f"📚 *Предмети групи {group_name}:*\n\n"
            for subj in group_subjects:
                subj_name = subj['subject_name'] if isinstance(subj, dict) else subj[1]
                teacher_name = subj['teacher_name'] if isinstance(subj, dict) else subj[2]
                if teacher_name:
                    response += f"• *{subj_name}* ({teacher_name})\n"
                else:
                    response += f"• *{subj_name}*\n"
            
            await message.answer(response, parse_mode="Markdown")
            return
    
    # Fallback: show all subjects from database
    subjects = get_all_subjects()
    
    if not subjects:
        # Add some default subjects
        default_subjects = [
            ("Вища математика", "ВМ", 4, "Курс вищої математики для технічних спеціальностей"),
            ("Програмування", "Прог", 8, "Основи програмування"),
            ("Дискретна математика", "ДМ", 4, "Дискретна математика для КН"),
            ("Алгоритми та структури даних", "АСД", 6, "Алгоритми та основні структури даних"),
            ("Бази даних", "БД", 5, "Проектування та використання БД"),
            ("Мережеві технології", "МТ", 4, "Комп'ютерні мережі"),
            ("Операційні системи", "ОС", 5, "Основи ОС"),
            ("Теорія ймовірностей", "ТЙ", 4, "Теорія ймовірностей та математична статистика"),
        ]
        
        from database.models import add_subject
        for name, short, credits, desc in default_subjects:
            add_subject(name, short, credits, desc)
        
        subjects = get_all_subjects()
    
    response = "📚 *Предмети:*\n\n"
    
    for subj in subjects:
        subj_name = subj['name'] if isinstance(subj, dict) else subj[1]
        short_name = subj['short_name'] if isinstance(subj, dict) else subj[2]
        credits = subj['credits'] if isinstance(subj, dict) else subj[3]
        response += f"• *{subj_name}*"
        if short_name:
            response += f" ({short_name})"
        response += f" - {credits} кредитів\n"
    
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("subject"))
async def subject_command(message: Message):
    """Handle /subject command - show details about a specific subject."""
    from database.models import get_subject_info
    
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "❌ Вкажіть назву предмету!\n"
            "Формат: `/subject Назва предмету`\n\n"
            "Приклад: `/subject Вища математика`",
            parse_mode="Markdown"
        )
        return
    
    subject_name = args[1].strip()
    subject_info = get_subject_info(subject_name)
    
    response = f"📖 *{subject_info['name']}*"
    if subject_info.get('short_name'):
        response += f" ({subject_info['short_name']})"
    response += f"\n📊 Кредити: {subject_info['credits']}\n"
    
    if subject_info.get('description'):
        response += f"\n📝 {subject_info['description']}\n"
    
    topics = subject_info.get('topics', [])
    if topics:
        response += "\n📚 *Теми:*\n"
        for topic in topics:
            response += f"• {topic}\n"
    
    await message.answer(response, parse_mode="Markdown")


# ============ Subject Management for Group Leaders and Teachers ============

class SubjectStates(StatesGroup):
    """FSM states for subject management."""
    waiting_for_subject_name = State()
    waiting_for_teacher_name = State()
    waiting_for_confirm = State()


@router.message(Command("add_subject"))
@role_required(allowed_roles=['group_leader', 'teacher', 'admin'])
async def add_subject_command(message: Message, state: FSMContext):
    """Handle /add_subject command - add a subject to the group."""
    user_id = message.from_user.id
    user = get_user(user_id)
    group_name = user['group_name'] if isinstance(user, dict) else user[1]
    
    if not group_name:
        await message.answer(
            "❌ Спочатку встановіть групу командою `/setgroup`",
            parse_mode="Markdown"
        )
        return
    
    await message.answer(
        f"📚 *Додавання предмету для групи {group_name}*\n\n"
        "Введіть назву предмету:",
        parse_mode="Markdown"
    )
    await state.set_state(SubjectStates.waiting_for_subject_name)


@router.message(SubjectStates.waiting_for_subject_name)
async def process_subject_name(message: Message, state: FSMContext):
    """Process subject name input."""
    subject_name = message.text.strip()
    
    if not subject_name:
        await message.answer("❌ Назва предмету не може бути порожньою!")
        return
    
    await state.update_data(subject_name=subject_name)
    
    user_id = message.from_user.id
    user = get_user(user_id)
    group_name = user['group_name'] if isinstance(user, dict) else user[1]
    
    await message.answer(
        f"📚 *{subject_name}* для групи {group_name}\n\n"
        "Введіть ім'я викладача (або '-' якщо невідомо):",
        parse_mode="Markdown"
    )
    await state.set_state(SubjectStates.waiting_for_teacher_name)


@router.message(SubjectStates.waiting_for_teacher_name)
async def process_teacher_name(message: Message, state: FSMContext):
    """Process teacher name input."""
    teacher_name = message.text.strip()
    if teacher_name == '-':
        teacher_name = None
    
    data = await state.get_data()
    subject_name = data['subject_name']
    
    user_id = message.from_user.id
    user = get_user(user_id)
    group_name = user['group_name'] if isinstance(user, dict) else user[1]
    
    # Add subject to group
    add_group_subject(group_name, subject_name, teacher_name)
    
    response = f"✅ *Предмет додано до групи {group_name}:*"
    response += f"\n📚 {subject_name}"
    if teacher_name:
        response += f"\n👨‍🏫 Викладач: {teacher_name}"
    
    await message.answer(response, parse_mode="Markdown")
    await state.clear()
    
    logger.info(f"Subject {subject_name} added to group {group_name} by user {user_id}")


@router.message(Command("my_subjects"))
@role_required(allowed_roles=['group_leader', 'teacher'])
async def my_subjects_command(message: Message):
    """Handle /my_subjects command - show subjects managed by the user."""
    user_id = message.from_user.id
    user = get_user(user_id)
    group_name = user['group_name'] if isinstance(user, dict) else user[1]
    user_name = user['full_name'] if isinstance(user, dict) else user[2]
    
    if not group_name:
        await message.answer(
            "❌ Спочатку встановіть групу командою `/setgroup`",
            parse_mode="Markdown"
        )
        return
    
    subjects = get_group_subjects(group_name)
    
    if not subjects:
        await message.answer(
            f"📚 У групі {group_name} немає предметів.\n\n"
            "Використайте `/add_subject` щоб додати предмет.",
            parse_mode="Markdown"
        )
        return
    
    response = f"📚 *Предмети групи {group_name}*\n\n"
    response += f"👨‍🏫 Викладач: {user_name}\n\n"
    
    for subj in subjects:
        subj_name = subj['subject_name'] if isinstance(subj, dict) else subj[1]
        teacher = subj['teacher_name'] if isinstance(subj, dict) else subj[2]
        response += f"• *{subj_name}*"
        if teacher:
            response += f" ({teacher})"
        response += "\n"
    
    response += "\n💡 Видаліть предмети через адміністратора (/admin_help)"
    
    await message.answer(response, parse_mode="Markdown")

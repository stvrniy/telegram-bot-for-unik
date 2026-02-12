"""
Cabinet handlers for SumDU Student Cabinet integration.
Allows students to view their academic data.
"""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup

from database.models import get_user
from services.sumdu_cabinet import (
    get_mock_student,
    get_mock_grades
)

logger = logging.getLogger(__name__)

router = Router()


class CabinetStates(StatesGroup):
    """FSM states for cabinet operations."""
    waiting_for_semester = State()


def format_student_profile(student) -> str:
    """Форматувати профіль студента."""
    return (
        f"👤 *Профіль студента*\n\n"
        f"📝 *{student.first_name} {student.last_name} {student.middle_name}*\n\n"
        f"🏫 Група: *{student.group_name}*\n"
        f"🏢 Факультет: *{student.faculty}*\n"
        f"📚 Курс: *{student.course}*\n\n"
        f"🎫 Студентський: *{student.student_ticket}*\n"
        f"📧 Email: *{student.email or 'Немає'}*\n"
        f"📱 Телефон: *{student.phone or 'Немає'}*"
    )


def format_subjects_list(subjects: list, group_name: str) -> str:
    """Форматувати список предметів."""
    response = f"📚 *Предмети групи {group_name}*\n\n"
    
    # Group by presence of grade
    with_grades = []
    without_grades = []
    
    for subj in subjects:
        if subj.grade:
            with_grades.append(subj)
        else:
            without_grades.append(subj)
    
    if with_grades:
        response += "✅ *З оцінками:*\n"
        for subj in with_grades:
            response += (
                f"\n📖 *{subj.name}*\n"
                f"   🏷️ {subj.short_name} | 📊 {subj.credits} кр.\n"
                f"   👨‍🏫 {subj.teacher_name}\n"
                f"   🎯 Оцінка: *{subj.grade}*"
            )
        response += "\n"
    
    if without_grades:
        response += "\n📝 *Без оцінок:*\n"
        for subj in without_grades:
            response += (
                f"\n📖 *{subj.name}*\n"
                f"   🏷️ {subj.short_name} | 📊 {subj.credits} кр.\n"
                f"   👨‍🏫 {subj.teacher_name}"
            )
        response += "\n"
    
    # Add summary
    total_credits = sum(s.credits for s in subjects)
    response += f"\n---\n📊 Всього кредитів: *{total_credits}*"
    
    return response


def format_grades_list(grades: list) -> str:
    """Форматувати список оцінок."""
    if not grades:
        return "📭 Оцінок поки що немає"
    
    response = "📊 *Ваші оцінки:*\n\n"
    
    total_points = 0
    count = 0
    
    for grade in grades:
        response += (
            f"📖 *{grade.subject_name}*\n"
            f"   🎯 Оцінка: *{grade.grade}* ({grade.grade_type})\n"
            f"   📅 {grade.date} | 👨‍🏫 {grade.teacher}\n"
        )
        
        if grade.points:
            try:
                points = int(grade.points.split('/')[0])
                total_points += points
                count += 1
            except Exception:
                pass
        response += "\n"
    
    if count > 0:
        avg = total_points / count
        response += f"\n---\n📈 Середній бал: *{avg:.1f}* / 100"
    
    return response


@router.message(Command("cabinet"))
@router.message(Command("profile"))
async def cabinet_command(message: Message):
    """Handle /cabinet command - show student profile."""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`",
            parse_mode="Markdown"
        )
        return
    
    # Для демонстрації використовуємо мок-дані
    # В реальному режимі потрібна авторизація через WebApp
    group_name = user['group_name'] if isinstance(user, dict) else user[1]
    
    student = get_mock_student(group_name)
    response = format_student_profile(student)
    
    # Add buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📚 Мої предмети", callback_data="my_subjects"),
            InlineKeyboardButton(text="📊 Мої оцінки", callback_data="my_grades")
        ],
        [
            InlineKeyboardButton(text="🔗 Увійти в кабінет", callback_data="login_cabinet")
        ]
    ])
    
    await message.answer(response, reply_markup=keyboard, parse_mode="Markdown")


async def grades_command(message: Message):
    """Handle /grades command - show student's grades."""
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
    
    # Используем мок-данные
    grades = get_mock_grades()
    response = format_grades_list(grades)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Предмети", callback_data="my_subjects")]
    ])
    
    await message.answer(response, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("debts"))
async def debts_command(message: Message):
    """Handle /debts command - show student's financial debts."""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`",
            parse_mode="Markdown"
        )
        return
    
    response = (
        "💰 *Фінансова інформація*\n\n"
        "✅ У вас немає заборгованостей!\n\n"
        "📝 *Інформація:*\n"
        "• Заборгованість з оплати за навчання: *0 грн*\n"
        "• Заборгованість за гуртожиток: *0 грн*\n"
        "• Інші платежі: *0 грн*"
    )
    
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("session"))
async def session_command(message: Message):
    """Handle /session command - show session info."""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`",
            parse_mode="Markdown"
        )
        return
    
    response = (
        "📅 *Сесія 2024/2025*\n\n"
        "📚 *Поточний семестр:* 6\n\n"
        "📝 *Стан сесії:*\n"
        "• 📅 Дата початку: 01.02.2025\n"
        "• 📅 Дата закінчення: 15.06.2025\n"
        "• 📊 Заліково-екзаменаційна сесія: 01.06.2025 - 15.06.2025\n\n"
        "✅ *Ваш статус:* Допущений до сесії\n"
        "📝 *Всього предметів:* 6\n"
        "✅ *Здано:* 2\n"
        "⏳ *Очікують:* 4"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Мої оцінки", callback_data="my_grades")]
    ])
    
    await message.answer(response, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("mycabinet"))
@router.message(Command("my"))
async def my_cabinet_command(message: Message):
    """Handle /mycabinet command - show all student info."""
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
    
    student = get_mock_student(group_name)
    response = format_student_profile(student)
    
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("cabinet_login"))
async def cabinet_login_command(message: Message):
    """Handle /cabinet_login command - login to cabinet."""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer(
            "❌ Спочатку запустіть бота командою `/start`",
            parse_mode="Markdown"
        )
        return
    
    response = (
        "🔐 *Вхід в кабінет студента*\n\n"
        "Для входу в кабінет студента СумДУ:\n\n"
        "1. Перейдіть за посиланням нижче\n"
        "2. Авторизуйтесь через Telegram\n"
        "3. Дозвольте доступ до даних\n\n"
        "📎 *Посилання:*\n"
        "https://t.me/your_bot_name?startapp=cabinet\n\n"
        "💡 *Примітка:*\n"
        "Для повної інтеграції потрібно налаштувати "
        "Telegram WebApp та API кабінету."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Відкрити кабінет", url="https://t.me/your_bot_name?startapp=cabinet")]
    ])
    
    await message.answer(response, reply_markup=keyboard, parse_mode="Markdown")

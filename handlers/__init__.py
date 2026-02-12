"""Handlers package for the Telegram Education Bot."""

from .student_commands import router as student_router
from .admin_commands import router as admin_router
from .communication import router as communication_router
from .cabinet import router as cabinet_router
from .ics_schedule import router as ics_router
from .teacher_commands import router as teacher_router

__all__ = [
    "student_router",
    "admin_router",
    "communication_router",
    "cabinet_router",
    "ics_router",
    "teacher_router",
]

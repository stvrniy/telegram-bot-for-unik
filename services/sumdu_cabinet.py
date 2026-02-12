"""
SumDU Cabinet Service - Авторизація та отримання даних з кабінету студента.
Використовує Telegram WebApp для авторизації.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
import base64
import json

import httpx
from cachetools import TTLCache

from config.settings import settings

logger = logging.getLogger(__name__)

# SumDU Cabinet URLs
SUMDU_CABINET_URL = "https://cabinet.sumdu.edu.ua"
SUMDU_API_BASE = "https://api.sumdu.edu.ua"


@dataclass
class Student:
    """Дані студента з кабінету."""

    id: str
    first_name: str
    last_name: str
    middle_name: str
    group_name: str
    group_id: str
    faculty: str
    course: int
    student_ticket: str
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass
class Subject:
    """Предмет з кабінету."""

    id: str
    name: str
    short_name: str
    credits: float
    semester: int
    teacher_name: str
    grade: Optional[str] = None
    grade_date: Optional[str] = None


@dataclass
class GradeItem:
    """Оцінка за предмет."""

    subject_name: str
    subject_id: str
    grade: str
    grade_type: str  # Атестація, Іспит, Залік
    date: str
    teacher: str
    points: Optional[str] = None


@dataclass
class FinancialDebt:
    """Фінансова заборгованість."""

    type: str  # contract, dormitory
    description: str
    amount: str
    due_date: Optional[str] = None


class SumDUCabinetService:
    """
    Сервіс для авторизації та отримання даних з кабінету студента.

    Авторизація відбувається через Telegram WebApp data.
    """

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self._cache = TTLCache(maxsize=100, ttl=3600)  # 1 hour cache
        self._auth_tokens: Dict[str, str] = {}  # user_id -> token

    async def close(self):
        """Закрити HTTP клієнт."""
        await self.client.aclose()

    def validate_telegram_webapp_data(
        self, webapp_data: str, bot_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Валідувати дані від Telegram WebApp.

        Args:
            webapp_data: Дані з WebApp (query_id=...&...)
            bot_token: Токен бота для валідації

        Returns:
            Словник з даними користувача або None
        """
        try:
            # Розпарсити дані
            data = dict(item.split("=") for item in webapp_data.split("&"))

            # Отримати hash
            received_hash = data.pop("hash", None)
            data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))

            # Перевірити hash
            secret_key = hashlib.sha256(bot_token.encode()).digest()
            calculated_hash = hmac.new(
                secret_key, data_check_string.encode(), hashlib.sha256
            ).hexdigest()

            if received_hash != calculated_hash:
                logger.warning("Invalid WebApp hash")
                return None

            # Перевірити дату
            auth_date = int(data.get("auth_date", 0))
            current_time = datetime.now().timestamp()

            if current_time - auth_date > 86400:  # 24 hours
                logger.warning("WebApp data too old")
                return None

            # Розпарсити user_data
            user_data_str = data.get("user", "{}")
            user_data = json.loads(base64.b64decode(user_data_str).decode())

            return {
                "user_id": int(data.get("user_id")),
                "first_name": user_data.get("first_name"),
                "last_name": user_data.get("last_name"),
                "username": user_data.get("username"),
                "auth_date": auth_date,
                "start_param": data.get("start_param"),  # може містити group_id
            }

        except Exception as e:
            logger.error(f"Error validating WebApp data: {e}")
            return None

    async def get_student_from_api(self, student_id: str) -> Optional[Student]:
        """
        Отримати дані студента з API кабінету.

        Args:
            student_id: ID студента в системі SumDU

        Returns:
            Об'єкт Student або None
        """
        try:
            response = await self.client.get(
                f"{SUMDU_API_BASE}/students/{student_id}",
                headers={"Authorization": f"Bearer {self._get_api_token()}"},
            )

            if response.status_code == 200:
                data = response.json()
                return Student(
                    id=data.get("id", ""),
                    first_name=data.get("firstName", ""),
                    last_name=data.get("lastName", ""),
                    middle_name=data.get("middleName", ""),
                    group_name=data.get("group", {}).get("name", ""),
                    group_id=data.get("group", {}).get("id", ""),
                    faculty=data.get("faculty", ""),
                    course=data.get("course", 1),
                    student_ticket=data.get("studentTicket", ""),
                    phone=data.get("phone"),
                    email=data.get("email"),
                )

        except Exception as e:
            logger.error(f"Error getting student data: {e}")

        return None

    async def get_student_subjects(
        self, student_id: str, semester: Optional[int] = None
    ) -> List[Subject]:
        """
        Отримати список предметів студента.

        Args:
            student_id: ID студента
            semester: Номер семестру (None - поточний)

        Returns:
            Список предметів
        """
        cache_key = f"subjects_{student_id}_{semester}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            url = f"{SUMDU_API_BASE}/students/{student_id}/subjects"
            params = {"semester": semester} if semester else {}

            response = await self.client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {self._get_api_token()}"},
            )

            if response.status_code == 200:
                data = response.json()
                subjects = []
                for item in data:
                    subjects.append(
                        Subject(
                            id=item.get("id", ""),
                            name=item.get("name", ""),
                            short_name=item.get("shortName", ""),
                            credits=float(item.get("credits", 0)),
                            semester=item.get("semester", 1),
                            teacher_name=item.get("teacher", {}).get("name", ""),
                            grade=item.get("grade"),
                            grade_date=item.get("gradeDate"),
                        )
                    )

                self._cache[cache_key] = subjects
                return subjects

        except Exception as e:
            logger.error(f"Error getting subjects: {e}")

        return []

    async def get_student_grades(
        self, student_id: str, semester: Optional[int] = None
    ) -> List[GradeItem]:
        """
        Отримати оцінки студента.

        Args:
            student_id: ID студента
            semester: Номер семестру

        Returns:
            Список оцінок
        """
        try:
            url = f"{SUMDU_API_BASE}/students/{student_id}/grades"
            params = {"semester": semester} if semester else {}

            response = await self.client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {self._get_api_token()}"},
            )

            if response.status_code == 200:
                data = response.json()
                grades = []
                for item in data:
                    grades.append(
                        GradeItem(
                            subject_name=item.get("subject", {}).get("name", ""),
                            subject_id=item.get("subject", {}).get("id", ""),
                            grade=item.get("grade", ""),
                            grade_type=item.get("gradeType", ""),
                            date=item.get("date", ""),
                            teacher=item.get("teacher", {}).get("name", ""),
                            points=item.get("points"),
                        )
                    )
                return grades

        except Exception as e:
            logger.error(f"Error getting grades: {e}")

        return []

    async def get_financial_debts(self, student_id: str) -> List[FinancialDebt]:
        """
        Отримати фінансові борги студента.

        Args:
            student_id: ID студента

        Returns:
            Список боргів
        """
        try:
            response = await self.client.get(
                f"{SUMDU_API_BASE}/students/{student_id}/debts",
                headers={"Authorization": f"Bearer {self._get_api_token()}"},
            )

            if response.status_code == 200:
                data = response.json()
                debts = []
                for item in data:
                    debts.append(
                        FinancialDebt(
                            type=item.get("type", ""),
                            description=item.get("description", ""),
                            amount=item.get("amount", ""),
                            due_date=item.get("dueDate"),
                        )
                    )
                return debts

        except Exception as e:
            logger.error(f"Error getting financial debts: {e}")

        return []

    async def get_session_info(self, student_id: str) -> Dict[str, Any]:
        """
        Отримати інформацію про сесію студента.

        Returns:
            Словник з даними сесії
        """
        try:
            response = await self.client.get(
                f"{SUMDU_API_BASE}/students/{student_id}/session",
                headers={"Authorization": f"Bearer {self._get_api_token()}"},
            )

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.error(f"Error getting session info: {e}")

        return {}

    def _get_api_token(self) -> str:
        """Отримати API токен для запитів."""
        # В реальному додатку потрібно реалізувати OAuth2 flow
        return settings.BOT_TOKEN

    def set_user_auth(self, user_id: int, student_id: str) -> None:
        """Зберегти авторизацію користувача."""
        self._auth_tokens[str(user_id)] = student_id

    def get_user_auth(self, user_id: int) -> Optional[str]:
        """Отримати ID студента для користувача."""
        return self._auth_tokens.get(str(user_id))

    def clear_user_auth(self, user_id: int) -> None:
        """Видалити авторизацію користувача."""
        self._auth_tokens.pop(str(user_id), None)


# Mock данные для тестування без реального API
def get_mock_student(group_name: str = "ІН-23") -> Student:
    """Повернути мок-дані студента."""
    return Student(
        id="12345",
        first_name="Іван",
        last_name="Іванов",
        middle_name="Іванович",
        group_name=group_name,
        group_id="group-123",
        faculty="Факультет комп'ютерних наук",
        course=3,
        student_ticket="КН-12345",
        phone="+380501234567",
        email="ivanov@stud.sumdu.edu.ua",
    )


def get_mock_subjects(group_name: str = "ІН-23") -> List[Subject]:
    """Повернути мок-дані предметів."""
    return [
        Subject(
            id="1",
            name="HR-менеджмент: основи лідерства",
            short_name="HR-лідерство",
            credits=5.0,
            semester=6,
            teacher_name="Проф. Коваленко О.М.",
            grade=None,
            grade_date=None,
        ),
        Subject(
            id="2",
            name="Кваліфікаційна робота бакалавра",
            short_name="Кваліфікаційна",
            credits=5.0,
            semester=6,
            teacher_name="Проф. Петров П.П.",
            grade=None,
            grade_date=None,
        ),
        Subject(
            id="3",
            name="Практика переддипломна",
            short_name="Практика",
            credits=5.0,
            semester=6,
            teacher_name="Доц. Сидоров С.С.",
            grade=None,
            grade_date=None,
        ),
        Subject(
            id="4",
            name="Розробка інтерактивних мультимедійних додатків",
            short_name="Мультимедіа",
            credits=4.0,
            semester=6,
            teacher_name="Доц. Козак Т.Т.",
            grade="90",
            grade_date="2025-01-15",
        ),
        Subject(
            id="5",
            name="Технічна підтримка програмного забезпечення",
            short_name="Техпідтримка",
            credits=4.0,
            semester=6,
            teacher_name="Інж. Бондар В.В.",
            grade="85",
            grade_date="2025-01-10",
        ),
        Subject(
            id="6",
            name="Технології захисту інформації",
            short_name="Захист інформації",
            credits=4.0,
            semester=6,
            teacher_name="Проф. Шевченко М.М.",
            grade=None,
            grade_date=None,
        ),
    ]


def get_mock_grades() -> List[GradeItem]:
    """Повернути мок-дані оцінок."""
    return [
        GradeItem(
            subject_name="Розробка інтерактивних мультимедійних додатків",
            subject_id="4",
            grade="90",
            grade_type="Іспит",
            date="2025-01-15",
            teacher="Доц. Козак Т.Т.",
            points="90/100",
        ),
        GradeItem(
            subject_name="Технічна підтримка програмного забезпечення",
            subject_id="5",
            grade="85",
            grade_type="Залік",
            date="2025-01-10",
            teacher="Інж. Бондар В.В.",
            points="85/100",
        ),
        GradeItem(
            subject_name="Технології захисту інформації",
            subject_id="6",
            grade="78",
            grade_type="Атестація",
            date="2025-01-20",
            teacher="Проф. Шевченко М.М.",
            points="78/100",
        ),
    ]


# Глобальний екземпляр сервісу
_cabinet_service: Optional[SumDUCabinetService] = None


async def get_cabinet_service() -> SumDUCabinetService:
    """Отримати або створити екземпляр сервісу."""
    global _cabinet_service
    if _cabinet_service is None:
        _cabinet_service = SumDUCabinetService()
    return _cabinet_service


async def close_cabinet_service():
    """Закрити сервіс."""
    global _cabinet_service
    if _cabinet_service is not None:
        await _cabinet_service.close()
        _cabinet_service = None

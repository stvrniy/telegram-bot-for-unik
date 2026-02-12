"""
SumDU API Service for fetching schedule and academic data.
Uses the public API from Sumy State University.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

import httpx
from cachetools import TTLCache

from config.settings import settings

logger = logging.getLogger(__name__)


# SumDU API Base URLs
SUMDU_API_BASE = "https://api.sumdu.edu.ua"
SUMDU_SCHEDULE_API = "https://schedule-api.sumdu.edu.ua"


@dataclass
class Group:
    """Represents a study group."""
    id: str
    name: str
    faculty: str
    course: int


@dataclass
class Teacher:
    """Represents a teacher."""
    id: str
    name: str
    position: str
    department: str
    email: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class Subject:
    """Represents an academic subject."""
    id: str
    name: str
    short_name: str
    credits: int
    teacher_id: Optional[str] = None


@dataclass
class ScheduleItem:
    """Represents a schedule item (lesson)."""
    date: str
    time_start: str
    time_end: str
    subject_name: str
    subject_short: str
    lesson_type: str  # lecture, practice, laboratory
    room: str
    building: str
    teacher_name: str
    group_name: str
    week_type: str  # numerator, denominator, both


class SumDUAPIService:
    """Service for interacting with SumDU public API."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        # Cache for 10 minutes to reduce API calls
        self._cache = TTLCache(maxsize=100, ttl=600)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def get_groups(self, faculty: Optional[str] = None) -> List[Group]:
        """
        Get list of all study groups.
        
        Args:
            faculty: Optional faculty name filter
            
        Returns:
            List of Group objects
        """
        cache_key = f"groups_{faculty}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Try different API endpoints
            endpoints = [
                f"{SUMDU_API_BASE}/groups",
                f"{SUMDU_SCHEDULE_API}/groups",
                f"{SUMDU_API_BASE}/api/groups"
            ]
            
            for endpoint in endpoints:
                try:
                    response = await self.client.get(endpoint, follow_redirects=True)
                    if response.status_code == 200:
                        data = response.json()
                        groups = self._parse_groups(data, faculty)
                        if groups:
                            self._cache[cache_key] = groups
                            return groups
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} failed: {e}")
                    continue
            
            # If API not available, return empty list
            logger.warning("SumDU API not accessible, using mock data")
            return self._get_mock_groups()
            
        except Exception as e:
            logger.error(f"Error fetching groups: {e}")
            return self._get_mock_groups()
    
    async def get_group_schedule(
        self, 
        group_name: str, 
        date: Optional[str] = None
    ) -> List[ScheduleItem]:
        """
        Get schedule for a specific group.
        
        Args:
            group_name: Name of the group (e.g., КС-21)
            date: Optional date in YYYY-MM-DD format
            
        Returns:
            List of ScheduleItem objects
        """
        cache_key = f"schedule_{group_name}_{date}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Try API endpoints
            endpoints = [
                f"{SUMDU_SCHEDULE_API}/groups/{group_name}/schedule",
                f"{SUMDU_API_BASE}/schedule/groups/{group_name}",
                f"{SUMDU_API_BASE}/api/schedule/{group_name}"
            ]
            
            for endpoint in endpoints:
                try:
                    response = await self.client.get(endpoint)
                    if response.status_code == 200:
                        data = response.json()
                        items = self._parse_schedule(data)
                        if items:
                            self._cache[cache_key] = items
                            return items
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} failed: {e}")
                    continue
            
            # If API not available, return mock data
            logger.warning(f"SumDU API not accessible for group {group_name}")
            return self._get_mock_schedule(group_name)
            
        except Exception as e:
            logger.error(f"Error fetching schedule for {group_name}: {e}")
            return self._get_mock_schedule(group_name)
    
    async def get_teachers(self, department: Optional[str] = None) -> List[Teacher]:
        """
        Get list of teachers.
        
        Args:
            department: Optional department filter
            
        Returns:
            List of Teacher objects
        """
        cache_key = f"teachers_{department}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            endpoints = [
                f"{SUMDU_API_BASE}/teachers",
                f"{SUMDU_SCHEDULE_API}/teachers",
                f"{SUMDU_API_BASE}/api/teachers"
            ]
            
            for endpoint in endpoints:
                try:
                    response = await self.client.get(endpoint)
                    if response.status_code == 200:
                        data = response.json()
                        teachers = self._parse_teachers(data, department)
                        if teachers:
                            self._cache[cache_key] = teachers
                            return teachers
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} failed: {e}")
                    continue
            
            return self._get_mock_teachers()
            
        except Exception as e:
            logger.error(f"Error fetching teachers: {e}")
            return self._get_mock_teachers()
    
    async def get_teacher_schedule(
        self, 
        teacher_id: str, 
        date: Optional[str] = None
    ) -> List[ScheduleItem]:
        """Get schedule for a specific teacher."""
        try:
            endpoints = [
                f"{SUMDU_SCHEDULE_API}/teachers/{teacher_id}/schedule",
                f"{SUMDU_API_BASE}/schedule/teachers/{teacher_id}"
            ]
            
            for endpoint in endpoints:
                try:
                    response = await self.client.get(endpoint)
                    if response.status_code == 200:
                        data = response.json()
                        return self._parse_schedule(data)
                except Exception:
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching teacher schedule: {e}")
            return []
    
    async def get_subjects(self) -> List[Subject]:
        """Get list of all subjects."""
        cache_key = "subjects"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            endpoints = [
                f"{SUMDU_API_BASE}/subjects",
                f"{SUMDU_SCHEDULE_API}/subjects",
                f"{SUMDU_API_BASE}/api/subjects"
            ]
            
            for endpoint in endpoints:
                try:
                    response = await self.client.get(endpoint)
                    if response.status_code == 200:
                        data = response.json()
                        subjects = self._parse_subjects(data)
                        if subjects:
                            self._cache[cache_key] = subjects
                            return subjects
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} failed: {e}")
                    continue
            
            return self._get_mock_subjects()
            
        except Exception as e:
            logger.error(f"Error fetching subjects: {e}")
            return self._get_mock_subjects()
    
    def _parse_groups(
        self, 
        data: Any, 
        faculty: Optional[str] = None
    ) -> List[Group]:
        """Parse groups from API response."""
        groups = []
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    group = Group(
                        id=item.get('id', ''),
                        name=item.get('name', ''),
                        faculty=item.get('faculty', ''),
                        course=item.get('course', 1)
                    )
                    if not faculty or faculty.lower() in group.faculty.lower():
                        groups.append(group)
        
        return groups
    
    def _parse_schedule(self, data: Any) -> List[ScheduleItem]:
        """Parse schedule from API response."""
        items = []
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    schedule_item = ScheduleItem(
                        date=item.get('date', ''),
                        time_start=item.get('timeStart', ''),
                        time_end=item.get('timeEnd', ''),
                        subject_name=item.get('subject', {}).get('name', ''),
                        subject_short=item.get('subject', {}).get('shortName', ''),
                        lesson_type=item.get('lessonType', ''),
                        room=item.get('room', ''),
                        building=item.get('building', ''),
                        teacher_name=item.get('teacher', {}).get('name', ''),
                        group_name=item.get('group', {}).get('name', ''),
                        week_type=item.get('weekType', 'both')
                    )
                    items.append(schedule_item)
        
        return items
    
    def _parse_teachers(
        self, 
        data: Any, 
        department: Optional[str] = None
    ) -> List[Teacher]:
        """Parse teachers from API response."""
        teachers = []
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    teacher = Teacher(
                        id=item.get('id', ''),
                        name=item.get('name', ''),
                        position=item.get('position', ''),
                        department=item.get('department', ''),
                        email=item.get('email'),
                        phone=item.get('phone')
                    )
                    if not department or department.lower() in teacher.department.lower():
                        teachers.append(teacher)
        
        return teachers
    
    def _parse_subjects(self, data: Any) -> List[Subject]:
        """Parse subjects from API response."""
        subjects = []
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    subject = Subject(
                        id=item.get('id', ''),
                        name=item.get('name', ''),
                        short_name=item.get('shortName', ''),
                        credits=item.get('credits', 0),
                        teacher_id=item.get('teacherId')
                    )
                    subjects.append(subject)
        
        return subjects
    
    def _get_mock_groups(self) -> List[Group]:
        """Return mock groups data for testing."""
        return [
            Group(id="1", name="КС-21", faculty="Факультет комп'ютерних наук", course=2),
            Group(id="2", name="КС-22", faculty="Факультет комп'ютерних наук", course=2),
            Group(id="3", name="ІП-31", faculty="Факультет інформаційних технологій", course=3),
            Group(id="4", name="ММ-11", faculty="Механіко-математичний факультет", course=1),
        ]
    
    def _get_mock_schedule(self, group_name: str) -> List[ScheduleItem]:
        """Return mock schedule data for testing."""
        today = datetime.now().date().isoformat()
        
        return [
            ScheduleItem(
                date=today,
                time_start="08:30",
                time_end="10:05",
                subject_name="Вища математика",
                subject_short="Вища математика",
                lesson_type="lecture",
                room="301",
                building="Головний корпус",
                teacher_name="Проф. Іванов І.І.",
                group_name=group_name,
                week_type="both"
            ),
            ScheduleItem(
                date=today,
                time_start="10:25",
                time_end="12:00",
                subject_name="Програмування",
                subject_short="Програмування",
                lesson_type="practice",
                room="405",
                building="Корпус ІТ",
                teacher_name="Доц. Петров П.П.",
                group_name=group_name,
                week_type="both"
            ),
        ]
    
    def _get_mock_teachers(self) -> List[Teacher]:
        """Return mock teachers data for testing."""
        return [
            Teacher(
                id="1",
                name="Іванов Іван Іванович",
                position="Професор",
                department="Кафедра вищої математики",
                email="ivanov@sumdu.edu.ua"
            ),
            Teacher(
                id="2",
                name="Петров Петро Петрович",
                position="Доцент",
                department="Кафедра програмної інженерії",
                email="petrov@sumdu.edu.ua"
            ),
        ]
    
    def _get_mock_subjects(self) -> List[Subject]:
        """Return mock subjects data for testing."""
        return [
            Subject(id="1", name="Вища математика", short_name="ВМ", credits=4),
            Subject(id="2", name="Програмування", short_name="Прог", credits=8),
            Subject(id="3", name="Дискретна математика", short_name="ДМ", credits=4),
            Subject(id="4", name="Алгоритми та структури даних", short_name="АСД", credits=6),
            Subject(id="5", name="Бази даних", short_name="БД", credits=5),
        ]


# Global service instance
_sumdu_service: Optional[SumDUAPIService] = None


async def get_sumdu_service() -> SumDUAPIService:
    """Get or create the SumDU API service instance."""
    global _sumdu_service
    if _sumdu_service is None:
        _sumdu_service = SumDUAPIService()
    return _sumdu_service


async def close_sumdu_service():
    """Close the SumDU API service."""
    global _sumdu_service
    if _sumdu_service is not None:
        await _sumdu_service.close()
        _sumdu_service = None

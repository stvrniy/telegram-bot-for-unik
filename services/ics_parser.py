"""
iCalendar (.ics) Parser Service.
Parses schedule from iCalendar format used by SumDU Cabinet.
"""

import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from dateutil import tz


logger = logging.getLogger(__name__)


@dataclass
class ICSEvent:
    """Parsed event from iCalendar format."""

    uid: str
    summary: str
    description: str
    location: str
    dtstart: datetime
    dtend: datetime
    dtstamp: datetime
    event_class: str = "PUBLIC"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uid": self.uid,
            "summary": self.summary,
            "description": self.description,
            "location": self.location,
            "dtstart": self.dtstart.isoformat(),
            "dtend": self.dtend.isoformat(),
            "dtstamp": self.dtstamp.isoformat(),
            "event_class": self.event_class,
        }


class ICSParser:
    """Parser for iCalendar (.ics) files."""

    # Patterns for parsing
    PATTERNS = {
        "uid": r"UID:(.+?)(?:\r?\n|$)",
        "summary": r"SUMMARY:(.+?)(?:\r?\n|$)",
        "description": r"DESCRIPTION:(.+?)(?:\r?\n|$)",
        "location": r"LOCATION:(.+?)(?:\r?\n|$)",
        "dtstamp": r"DTSTAMP:(\d{8}T\d{6}Z)",
        "dtstart": r"DTSTART(?:;[^:]*)?:(\d{8}T\d{6}(?:Z|[+-]\d{4})?)",
        "dtend": r"DTEND(?:;[^:]*)?:(\d{8}T\d{6}(?:Z|[+-]\d{4})?)",
        "class": r"CLASS:(.+?)(?:\r?\n|$)",
        "alarm_trigger": r"TRIGGER:-?PT(\d+)([HMS])",
    }

    def parse(self, ics_content: str) -> List[ICSEvent]:
        """
        Parse iCalendar content and return list of events.

        Args:
            ics_content: Raw iCalendar content

        Returns:
            List of parsed ICSEvent objects
        """
        events = []

        # Split by VEVENT blocks
        event_blocks = self._split_events(ics_content)

        for block in event_blocks:
            try:
                event = self._parse_event(block)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error(f"Error parsing event: {e}")
                continue

        logger.info(f"Parsed {len(events)} events from iCalendar")
        return events

    def _split_events(self, content: str) -> List[str]:
        """Split content into individual VEVENT blocks."""
        # Remove line folding (lines ending with whitespace continue on next line)
        content = self._unfold_lines(content)

        # Find all VEVENT blocks
        pattern = r"BEGIN:VEVENT(.+?)END:VEVENT"
        matches = re.findall(pattern, content, re.DOTALL)
        return matches

    def _unfold_lines(self, content: str) -> str:
        """Remove iCalendar line folding (RFC 5545)."""
        # Lines starting with whitespace are continuations
        return re.sub(r"\r?\n[ \t]+", "", content)

    def _parse_event(self, block: str) -> Optional[ICSEvent]:
        """Parse a single VEVENT block."""
        # Parse DTSTART and DTEND with timezone
        dtstart_str = self._extract_value(block, "dtstart")
        dtend_str = self._extract_value(block, "dtend")
        dtstamp_str = self._extract_value(block, "dtstamp")

        if not dtstart_str:
            logger.warning("Event missing DTSTART, skipping")
            return None

        # Parse datetime
        try:
            # Handle timezone
            tz_info = tz.gettz("Europe/Kiev")

            dtstart = self._parse_datetime(dtstart_str, tz_info)
            dtend = (
                self._parse_datetime(dtend_str, tz_info)
                if dtend_str
                else dtstart + timedelta(hours=1)
            )
            dtstamp = (
                self._parse_datetime(dtstamp_str, tz.UTC)
                if dtstamp_str
                else datetime.now(tz.UTC)
            )

        except Exception as e:
            logger.error(f"Error parsing datetime: {e}")
            return None

        # Extract other fields
        summary = self._extract_value(block, "summary") or "Без назви"
        description = self._extract_value(block, "description") or ""
        location = self._extract_value(block, "location") or ""
        event_class = self._extract_value(block, "class") or "PUBLIC"
        uid = self._extract_value(block, "uid") or ""

        # Clean up summary (remove type in parentheses)
        summary = self._clean_summary(summary)

        return ICSEvent(
            uid=uid,
            summary=summary,
            description=description,
            location=location,
            dtstart=dtstart,
            dtend=dtend,
            dtstamp=dtstamp,
            event_class=event_class,
        )

    def _extract_value(self, block: str, field_name: str) -> Optional[str]:
        """Extract a value from event block."""
        pattern = self.PATTERNS.get(field_name)
        if not pattern:
            return None

        match = re.search(pattern, block, re.IGNORECASE)
        if match:
            value = match.group(1)
            # Unescape special characters
            value = value.replace("\\n", "\n").replace("\\,", ",")
            return value.strip()
        return None

    def _parse_datetime(self, dt_str: str, tz_info) -> datetime:
        """Parse datetime string to datetime object."""
        # Format: YYYYMMDDTHHMMSS or YYYYMMDDTHHMMSSZ
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1]
            tz_info = tz.UTC

        # Parse the format
        if len(dt_str) == 15 and dt_str[8] == "T":
            dt_obj = datetime.strptime(dt_str, "%Y%m%dT%H%M%S")
        else:
            # Handle timezone offset
            if "+" in dt_str:
                base, offset = dt_str.split("+")
                dt_obj = datetime.strptime(base, "%Y%m%dT%H%M%S")
                dt_obj = dt_obj.replace(tzinfo=tz_info)
            else:
                dt_obj = datetime.strptime(dt_str, "%Y%m%dT%H%M%S")
                dt_obj = dt_obj.replace(tzinfo=tz_info)
                return dt_obj

        if not dt_obj.tzinfo:
            dt_obj = dt_obj.replace(tzinfo=tz_info)

        return dt_obj

    def _clean_summary(self, summary: str) -> str:
        """Clean summary field."""
        # Remove type in parentheses (e.g., "(лабораторне заняття)")
        summary = re.sub(r"\s*\([^)]*\)\s*", "", summary)
        return summary.strip()

    def format_for_display(self, events: List[ICSEvent]) -> str:
        """Format events for display in Telegram."""
        if not events:
            return "📭 Немає подій"

        response = "📅 *Розклад занять*\n\n"

        # Group by date
        by_date = {}
        for event in events:
            date_key = event.dtstart.strftime("%Y-%m-%d")
            if date_key not in by_date:
                by_date[date_key] = []
            by_date[date_key].append(event)

        # Sort dates
        for date_key in sorted(by_date.keys()):
            events_on_date = by_date[date_key]

            # Format date
            date_obj = datetime.strptime(date_key, "%Y-%m-%d")
            date_formatted = date_obj.strftime("%d.%m.%Y (%A)")
            day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"][date_obj.weekday()]
            date_formatted = date_obj.strftime(f"%d.%m.%Y ({day_name})")

            response += f"📆 *{date_formatted}*\n"

            # Sort by time
            events_on_date.sort(key=lambda e: e.dtstart)

            for event in events_on_date:
                time_start = event.dtstart.strftime("%H:%M")
                time_end = event.dtend.strftime("%H:%M")

                # Determine event type emoji
                emoji = self._get_event_emoji(event.summary)

                response += (
                    f"{emoji} *{time_start} - {time_end}*\n   📖 {event.summary}\n"
                )

                if event.description:
                    # Extract teacher name from description
                    teacher = self._extract_teacher(event.description)
                    if teacher:
                        response += f"   👨‍🏫 {teacher}\n"

                response += "\n"

            response += "\n"

        return response

    def _get_event_emoji(self, summary: str) -> str:
        """Get emoji based on event summary."""
        summary_lower = summary.lower()

        if "лекція" in summary_lower:
            return "📚"
        elif "лаборатор" in summary_lower:
            return "🔬"
        elif "практичн" in summary_lower:
            return "✍️"
        elif "семінар" in summary_lower:
            return "💬"
        elif "іспит" in summary_lower or "екзамен" in summary_lower:
            return "📝"
        elif "залік" in summary_lower:
            return "✅"
        elif "консультац" in summary_lower:
            return "💡"
        else:
            return "📌"

    def _extract_teacher(self, description: str) -> Optional[str]:
        """Extract teacher name from description."""
        # Teacher name is usually first line before newline
        if "\n" in description:
            first_line = description.split("\n")[0].strip()
            # Clean up
            if first_line and len(first_line) > 3:
                return first_line
        return None


def parse_ics_content(ics_content: str) -> List[ICSEvent]:
    """Parse iCalendar content and return events."""
    parser = ICSParser()
    return parser.parse(ics_content)


def format_schedule_from_ics(ics_content: str) -> str:
    """Parse iCalendar content and format for display."""
    events = parse_ics_content(ics_content)
    parser = ICSParser()
    return parser.format_for_display(events)


# Sample .ics content for testing
SAMPLE_ICS_CONTENT = """BEGIN:VCALENDAR
X-WR-CALNAME:Розклад занять СумДУ
X-WR-TIMEZONE:Europe/Kiev
X-PUBLISHED-TTL:PT12H
METHOD:PUBLISH
VERSION:2.0
BEGIN:VEVENT
UID:4d7fc4d07f88bab3bb125df3a18dbe7e@sh.cabinet.sumdu.edu.ua
DTSTAMP:20260116T120325Z
DTSTART;TZID=Europe/Kiev:20260212T114000
DTEND;TZID=Europe/Kiev:20260212T130000
SUMMARY:Технології захисту інформації (лабораторне заняття)
LOCATION:
DESCRIPTION:Пугач Ігор Олександрович\\nІН-23\\n\\nhttps://sh.cabinet.sumdu.edu.ua/
CLASS:PUBLIC
END:VEVENT
BEGIN:VEVENT
UID:3e3b0f8cec52218e1e5c0da1b1424c7a@sh.cabinet.sumdu.edu.ua
DTSTAMP:20260128T150112Z
DTSTART;TZID=Europe/Kiev:20260212T140000
DTEND;TZID=Europe/Kiev:20260212T152000
SUMMARY:Технічна підтримка програмного забезпечення (лабораторне заняття)
LOCATION:
DESCRIPTION:Дегтярьов Владислав Валерійович\\nІН-23\\n\\nhttps://sh.cabinet.sumdu.edu.ua/
CLASS:PUBLIC
END:VEVENT
END:VCALENDAR"""

"""
Scheduler service for sending event reminders.
Uses APScheduler for efficient async scheduling.
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config.settings import settings
from database.models import get_events_for_date, get_users_for_group

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing event reminders."""

    def __init__(self, bot):
        """
        Initialize the scheduler service.

        Args:
            bot: Aiogram Bot instance
        """
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self._notified_events: set = set()  # Track notified events to avoid duplicates

    def start(self) -> None:
        """Start the scheduler with configured interval."""
        interval = settings.NOTIFICATION_INTERVAL_MINUTES

        self.scheduler.add_job(
            self.check_events,
            trigger=IntervalTrigger(minutes=interval),
            id="check_events",
            name="Check and send event reminders",
            replace_existing=True,
            next_run_time=datetime.now() + timedelta(seconds=10),
        )

        self.scheduler.start()
        logger.info(f"Scheduler started with {interval} minute interval")

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    async def check_events(self) -> None:
        """Check for events and send reminders."""
        now = datetime.now()
        date_str = now.date().isoformat()
        current_time = now.strftime(settings.TIME_FORMAT)

        # Get today's events
        events = get_events_for_date(date_str)

        if not events:
            logger.debug(f"No events found for {date_str}")
            return

        logger.info(f"Checking {len(events)} events for {date_str} at {current_time}")

        for event in events:
            event_id = event["id"] if isinstance(event, dict) else event[0]
            event_time = event["time"] if isinstance(event, dict) else event[2]

            # Skip if already notified
            if event_id in self._notified_events:
                continue

            # Check if it's time to notify (5 minutes before event)
            event_datetime = datetime.strptime(
                f"{date_str} {event_time}",
                f"{settings.DATE_FORMAT} {settings.TIME_FORMAT}",
            )
            notify_time = event_datetime - timedelta(minutes=5)

            if now >= notify_time:
                group_name = (
                    event["group_name"] if isinstance(event, dict) else event[5]
                )
                await self.send_event_reminder(event, group_name)

                # Mark as notified (in production, store in DB)
                self._notified_events.add(event_id)

                logger.info(f"Sent reminder for event #{event_id}")

    async def send_event_reminder(self, event, group_name: str) -> int:
        """
        Send reminder to all users in a group.

        Args:
            event: Event data (dict or tuple)
            group_name: Name of the group to notify

        Returns:
            Number of successfully sent notifications
        """
        users = get_users_for_group(group_name)

        if not users:
            logger.warning(f"No users found for group {group_name}")
            return 0

        # Extract event details
        if isinstance(event, dict):
            title = event["title"]
            time = event["time"]
            date = event["date"]
            room = event["room"]
        else:
            title = event[3]
            time = event[2]
            date = event[1]
            room = event[4]

        message = (
            f"⏰ *Нагадування про заняття!*\n\n"
            f"📝 *{title}*\n"
            f"⏰ {time} | 📅 {date}\n"
            f"🏫 Аудиторія: {room}\n"
            f"👥 Група: {group_name}"
        )

        sent_count = 0
        for user in users:
            user_id = user["user_id"] if isinstance(user, dict) else user[0]
            try:
                await self.bot.send_message(user_id, message, parse_mode="Markdown")
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")

        logger.info(
            f"Sent {sent_count}/{len(users)} notifications for group {group_name}"
        )
        return sent_count

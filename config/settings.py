"""
Configuration settings for the Telegram Education Bot.
Loads environment variables from .env file.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Set, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    ADMIN_IDS: Set[int] = field(
        default_factory=lambda: set(
            int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
        )
    )
    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///schedule.db")
    )
    NOTIFICATION_INTERVAL_MINUTES: int = field(
        default_factory=lambda: int(os.getenv("NOTIFICATION_INTERVAL_MINUTES", 15))
    )
    TIME_FORMAT: str = field(
        default_factory=lambda: os.getenv("TIME_FORMAT", "%H:%M")
    )
    DATE_FORMAT: str = field(
        default_factory=lambda: os.getenv("DATE_FORMAT", "%Y-%m-%d")
    )

    def is_valid(self) -> bool:
        """Validate that required settings are configured."""
        if not self.BOT_TOKEN:
            return False
        return True

    def get_db_path(self) -> str:
        """Get the database file path from DATABASE_URL."""
        if self.DATABASE_URL.startswith("sqlite:///"):
            return self.DATABASE_URL.replace("sqlite:///", "")
        return self.DATABASE_URL


# Global settings instance
settings = Settings()

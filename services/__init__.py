"""Services package for the Telegram Education Bot."""

from .scheduler import SchedulerService
from .sumdu_api import get_sumdu_service, close_sumdu_service, SumDUAPIService

__all__ = [
    "SchedulerService",
    "get_sumdu_service",
    "close_sumdu_service",
    "SumDUAPIService",
]

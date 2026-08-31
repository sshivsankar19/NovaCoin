import logging

from database.postgres import db
from database.repository.pool_analytics_repository import (
    PoolAnalyticsRepository,
)

logger = logging.getLogger(__name__)


class PoolAnalyticsService:
    @staticmethod
    def record(pool_id, commit=True, inactivity_seconds=120):
        try:
            return PoolAnalyticsRepository.record_snapshot(
                pool_id,
                commit=commit,
                inactivity_seconds=inactivity_seconds
            )
        except Exception:
            # Metrics are supplementary; the share/block transaction has
            # already committed when recording is normally requested.
            db.session.rollback()
            logger.warning(
                "Unable to persist pool analytics for pool %s",
                pool_id,
                exc_info=True
            )
            return None

    @staticmethod
    def statistics(pool_id, window_minutes=None):
        return PoolAnalyticsRepository.get_statistics(
            pool_id, window_minutes=window_minutes
        )

    @staticmethod
    def history(pool_id, page, page_size, since=None):
        return PoolAnalyticsRepository.get_history(
            pool_id, page=page, page_size=page_size, since=since
        )

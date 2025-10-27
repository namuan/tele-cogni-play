import structlog
from typing import Optional, Dict, Any
from datetime import datetime
from cogniplay.database.connection import DatabaseConnection

logger = structlog.get_logger()

class DifficultyRepository:
    """Repository for difficulty tracking operations"""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def create_tracking(self, user_id: int) -> Dict[str, Any]:
        """Create initial difficulty tracking for a user"""

        # Check if tracking already exists
        existing = self.db.fetchone(
            "SELECT * FROM difficulty_tracking WHERE user_id = ?",
            (user_id,)
        )

        if existing:
            return self._row_to_dict(existing)

        # Create new tracking
        self.db.execute(
            """
            INSERT INTO difficulty_tracking (user_id)
            VALUES (?)
            """,
            (user_id,)
        )

        logger.info("difficulty_tracking_created", user_id=user_id)

        # Return the created tracking
        row = self.db.fetchone(
            "SELECT * FROM difficulty_tracking WHERE user_id = ?",
            (user_id,)
        )
        return self._row_to_dict(row)

    async def get_tracking(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get difficulty tracking for a user"""

        row = self.db.fetchone(
            "SELECT * FROM difficulty_tracking WHERE user_id = ?",
            (user_id,)
        )

        if row:
            return self._row_to_dict(row)
        return None

    async def update_tracking(self, user_id: int, tracking_data: Dict[str, Any]):
        """Update difficulty tracking for a user"""

        self.db.execute(
            """
            UPDATE difficulty_tracking
            SET consecutive_successes = ?, consecutive_failures = ?,
                last_exercise_result = ?, last_updated = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (
                tracking_data['consecutive_successes'],
                tracking_data['consecutive_failures'],
                tracking_data['last_exercise_result'],
                user_id
            )
        )

        logger.debug(
            "difficulty_tracking_updated",
            user_id=user_id,
            successes=tracking_data['consecutive_successes'],
            failures=tracking_data['consecutive_failures']
        )

    async def reset_tracking(self, user_id: int):
        """Reset difficulty tracking counters"""

        self.db.execute(
            """
            UPDATE difficulty_tracking
            SET consecutive_successes = 0, consecutive_failures = 0,
                last_exercise_result = NULL, last_updated = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (user_id,)
        )

        logger.info("difficulty_tracking_reset", user_id=user_id)

    async def get_user_difficulty_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive difficulty statistics for a user"""

        tracking = self.get_tracking(user_id)

        if not tracking:
            return {
                'current_streak': {'type': None, 'count': 0},
                'total_adjustments': 0,
                'last_adjustment': None
            }

        # Determine current streak
        if tracking['consecutive_successes'] > 0:
            current_streak = {'type': 'success', 'count': tracking['consecutive_successes']}
        elif tracking['consecutive_failures'] > 0:
            current_streak = {'type': 'failure', 'count': tracking['consecutive_failures']}
        else:
            current_streak = {'type': None, 'count': 0}

        # Count total adjustments (this would require additional tracking)
        # For now, return basic stats
        return {
            'current_streak': current_streak,
            'last_result': tracking['last_exercise_result'],
            'last_updated': tracking['last_updated'],
            'tracking_active': True
        }

    async def get_all_tracking_stats(self) -> Dict[str, Any]:
        """Get global difficulty tracking statistics"""

        # Average consecutive successes/failures
        avg_successes = self.db.fetchone(
            "SELECT AVG(consecutive_successes) FROM difficulty_tracking",
            ()
        )[0] or 0

        avg_failures = self.db.fetchone(
            "SELECT AVG(consecutive_failures) FROM difficulty_tracking",
            ()
        )[0] or 0

        # Distribution of last results
        result_counts = self.db.fetchall(
            """
            SELECT last_exercise_result, COUNT(*) as count
            FROM difficulty_tracking
            WHERE last_exercise_result IS NOT NULL
            GROUP BY last_exercise_result
            """
        )

        return {
            'total_users_tracking': self.db.fetchone(
                "SELECT COUNT(*) FROM difficulty_tracking", ()
            )[0],
            'avg_consecutive_successes': avg_successes,
            'avg_consecutive_failures': avg_failures,
            'result_distribution': {row[0]: row[1] for row in result_counts}
        }

    async def cleanup_old_tracking(self, days_old: int = 30):
        """Reset tracking for users who haven't been active"""

        cutoff_date = (datetime.now().timestamp() - days_old * 24 * 3600)

        # Find users who haven't updated recently
        old_tracking = self.db.fetchall(
            """
            SELECT user_id FROM difficulty_tracking
            WHERE last_updated < ?
            """,
            (cutoff_date,)
        )

        reset_count = 0
        for row in old_tracking:
            self.reset_tracking(row[0])
            reset_count += 1

        if reset_count > 0:
            logger.info("old_difficulty_tracking_reset", count=reset_count)

        return reset_count

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary"""

        return {
            'tracking_id': row[0],
            'user_id': row[1],
            'consecutive_successes': row[2],
            'consecutive_failures': row[3],
            'last_exercise_result': row[4],
            'last_updated': row[5]
        }

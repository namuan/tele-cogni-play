import structlog
from typing import Optional, Dict, Any
from datetime import datetime
from cogniplay.database.connection import DatabaseConnection
from cogniplay.data.models import UserProfile

logger = structlog.get_logger()

class UserRepository:
    """Repository for user profile operations"""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def get_or_create_user(self, telegram_user_id: int, telegram_username: Optional[str] = None) -> Dict[str, Any]:
        """Get existing user or create new one"""

        # Check if user exists
        existing = self.db.fetchone(
            "SELECT * FROM user_profile WHERE telegram_user_id = ?",
            (telegram_user_id,)
        )

        if existing:
            # Update last active
            self.db.execute(
                "UPDATE user_profile SET last_active = CURRENT_TIMESTAMP WHERE telegram_user_id = ?",
                (telegram_user_id,)
            )
            return self._row_to_dict(existing)

        # Create new user
        self.db.execute(
            """
            INSERT INTO user_profile (user_id, telegram_user_id, telegram_username)
            VALUES (1, ?, ?)
            """,
            (telegram_user_id, telegram_username)
        )

        logger.info("user_created", telegram_user_id=telegram_user_id)

        # Return the created user
        user_row = self.db.fetchone(
            "SELECT * FROM user_profile WHERE telegram_user_id = ?",
            (telegram_user_id,)
        )
        return self._row_to_dict(user_row)

    async def get_user(self, user_id: int = 1) -> Optional[Dict[str, Any]]:
        """Get user profile by user_id"""

        row = self.db.fetchone(
            "SELECT * FROM user_profile WHERE user_id = ?",
            (user_id,)
        )

        if row:
            return self._row_to_dict(row)
        return None

    async def update_difficulty_level(self, user_id: int, new_level: int):
        """Update user's difficulty level"""

        self.db.execute(
            "UPDATE user_profile SET current_difficulty_level = ? WHERE user_id = ?",
            (new_level, user_id)
        )

        logger.info("difficulty_level_updated", user_id=user_id, new_level=new_level)

    async def update_settings(self, user_id: int, settings: Dict[str, Any]):
        """Update user settings"""

        # For now, just update last_active when settings change
        # Could be extended for more settings
        self.db.execute(
            "UPDATE user_profile SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )

    async def get_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics"""

        user = await self.get_user(user_id)
        if not user:
            return {}

        # Get recent performance (last 7 days)
        week_ago = (datetime.now().timestamp() - 7 * 24 * 3600)

        recent_results = self.db.fetchall(
            """
            SELECT er.score, er.accuracy, er.exercise_category
            FROM exercise_results er
            JOIN sessions s ON er.session_id = s.session_id
            WHERE s.user_id = ? AND er.timestamp > ?
            """,
            (user_id, week_ago)
        )

        if recent_results:
            avg_score = sum(row[0] for row in recent_results) / len(recent_results)
            avg_accuracy = sum(row[1] for row in recent_results) / len(recent_results)
        else:
            avg_score = 0
            avg_accuracy = 0

        # Get category breakdown
        category_stats = {}
        for row in recent_results:
            category = row[2]
            if category not in category_stats:
                category_stats[category] = {'count': 0, 'total_score': 0}
            category_stats[category]['count'] += 1
            category_stats[category]['total_score'] += row[0]

        for category, stats in category_stats.items():
            stats['avg_score'] = stats['total_score'] / stats['count']

        return {
            'user': user,
            'recent_avg_score': avg_score,
            'recent_avg_accuracy': avg_accuracy,
            'category_performance': category_stats,
            'total_sessions': user['total_sessions'],
            'total_exercises': user['total_exercises_completed'],
            'total_scenarios': user['total_scenarios_completed']
        }

    async def update_activity(self, user_id: int):
        """Update user's last active timestamp"""

        self.db.execute(
            "UPDATE user_profile SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )

    async def increment_session_count(self, user_id: int):
        """Increment total sessions count"""

        self.db.execute(
            "UPDATE user_profile SET total_sessions = total_sessions + 1 WHERE user_id = ?",
            (user_id,)
        )

    async def increment_exercise_count(self, user_id: int, count: int = 1):
        """Increment exercises completed count"""

        self.db.execute(
            "UPDATE user_profile SET total_exercises_completed = total_exercises_completed + ? WHERE user_id = ?",
            (count, user_id)
        )

    async def increment_scenario_count(self, user_id: int, count: int = 1):
        """Increment scenarios completed count"""

        self.db.execute(
            "UPDATE user_profile SET total_scenarios_completed = total_scenarios_completed + ? WHERE user_id = ?",
            (count, user_id)
        )

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary"""

        return {
            'user_id': row[0],
            'telegram_user_id': row[1],
            'telegram_username': row[2],
            'created_at': row[3],
            'last_active': row[4],
            'current_difficulty_level': row[5],
            'total_sessions': row[6],
            'total_exercises_completed': row[7],
            'total_scenarios_completed': row[8]
        }

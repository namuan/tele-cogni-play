import uuid
import structlog
from typing import Optional, Dict, Any, List
from datetime import datetime
from cogniplay.database.connection import DatabaseConnection

logger = structlog.get_logger()

class SessionRepository:
    """Repository for session operations"""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def create_session(
        self,
        user_id: int,
        session_type: str,
        difficulty_level: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new training session"""

        session_id = str(uuid.uuid4())

        self.db.execute(
            """
            INSERT INTO sessions (session_id, user_id, session_type, difficulty_level)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, user_id, session_type, difficulty_level)
        )

        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user_id,
            type=session_type
        )

        # Return session data
        return await self.get_session(session_id)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""

        row = self.db.fetchone(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,)
        )

        if row:
            return self._row_to_dict(row)
        return None

    async def get_active_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get the currently active session for a user"""

        row = self.db.fetchone(
            """
            SELECT * FROM sessions
            WHERE user_id = ? AND end_time IS NULL
            ORDER BY start_time DESC
            LIMIT 1
            """,
            (user_id,)
        )

        if row:
            return self._row_to_dict(row)
        return None

    async def complete_session(self, session_id: str, average_score: Optional[float] = None):
        """Mark session as completed"""

        self.db.execute(
            """
            UPDATE sessions
            SET end_time = CURRENT_TIMESTAMP, average_score = ?
            WHERE session_id = ?
            """,
            (average_score, session_id)
        )

        logger.info("session_completed", session_id=session_id, score=average_score)

    async def get_session_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent session history for a user"""

        rows = self.db.fetchall(
            """
            SELECT * FROM sessions
            WHERE user_id = ?
            ORDER BY start_time DESC
            LIMIT ?
            """,
            (user_id, limit)
        )

        return [self._row_to_dict(row) for row in rows]

    async def update_session_stats(
        self,
        session_id: str,
        exercises_completed: Optional[int] = None,
        scenarios_completed: Optional[int] = None,
        average_score: Optional[float] = None
    ):
        """Update session statistics"""

        updates = []
        params = []

        if exercises_completed is not None:
            updates.append("exercises_completed = ?")
            params.append(exercises_completed)

        if scenarios_completed is not None:
            updates.append("scenarios_completed = ?")
            params.append(scenarios_completed)

        if average_score is not None:
            updates.append("average_score = ?")
            params.append(average_score)

        if updates:
            query = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?"
            params.append(session_id)
            self.db.execute(query, tuple(params))

    async def get_sessions_by_date_range(
        self,
        user_id: int,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """Get sessions within a date range"""

        rows = self.db.fetchall(
            """
            SELECT * FROM sessions
            WHERE user_id = ? AND start_time >= ? AND start_time <= ?
            ORDER BY start_time DESC
            """,
            (user_id, start_date, end_date)
        )

        return [self._row_to_dict(row) for row in rows]

    async def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed session summary with results"""

        session = await self.get_session(session_id)
        if not session:
            return None

        # Get exercise results
        exercise_results = self.db.fetchall(
            """
            SELECT exercise_category, COUNT(*) as count, AVG(score) as avg_score
            FROM exercise_results
            WHERE session_id = ?
            GROUP BY exercise_category
            """,
            (session_id,)
        )

        # Get scenario results
        scenario_results = self.db.fetchall(
            """
            SELECT scenario_type, COUNT(*) as count, AVG(performance_score) as avg_score
            FROM scenario_results
            WHERE session_id = ?
            GROUP BY scenario_type
            """,
            (session_id,)
        )

        return {
            'session': session,
            'exercise_summary': [
                {'category': row[0], 'count': row[1], 'avg_score': row[2]}
                for row in exercise_results
            ],
            'scenario_summary': [
                {'type': row[0], 'count': row[1], 'avg_score': row[2]}
                for row in scenario_results
            ]
        }

    async def delete_session(self, session_id: str):
        """Delete a session (for cleanup/testing)"""

        self.db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        logger.warning("session_deleted", session_id=session_id)

    async def get_user_session_stats(self, user_id: int) -> Dict[str, Any]:
        """Get aggregate session statistics for a user"""

        # Total sessions
        total_sessions = self.db.fetchone(
            "SELECT COUNT(*) FROM sessions WHERE user_id = ?",
            (user_id,)
        )[0]

        # Average session duration (for completed sessions)
        avg_duration = self.db.fetchone(
            """
            SELECT AVG((julianday(end_time) - julianday(start_time)) * 24 * 60)
            FROM sessions
            WHERE user_id = ? AND end_time IS NOT NULL
            """,
            (user_id,)
        )[0] or 0

        # Sessions by type
        type_stats = self.db.fetchall(
            """
            SELECT session_type, COUNT(*), AVG(average_score)
            FROM sessions
            WHERE user_id = ?
            GROUP BY session_type
            """,
            (user_id,)
        )

        return {
            'total_sessions': total_sessions,
            'avg_duration_minutes': avg_duration,
            'type_breakdown': [
                {'type': row[0], 'count': row[1], 'avg_score': row[2] or 0}
                for row in type_stats
            ]
        }

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary"""

        return {
            'session_id': row[0],
            'user_id': row[1],
            'session_type': row[2],
            'start_time': row[3],
            'end_time': row[4],
            'difficulty_level': row[5],
            'exercises_completed': row[6],
            'scenarios_completed': row[7],
            'average_score': row[8]
        }

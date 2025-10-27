import uuid
import json
import structlog
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from cogniplay.database.connection import DatabaseConnection
from cogniplay.data.models import ExerciseResult, ScenarioOutcome

logger = structlog.get_logger()

class ProgressRepository:
    """Repository for progress tracking and analytics"""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def record_exercise_result(
        self,
        session_id: str,
        exercise,
        result: ExerciseResult
    ):
        """Record an exercise result"""

        result_id = str(uuid.uuid4())

        self.db.execute(
            """
            INSERT INTO exercise_results (
                result_id, session_id, exercise_category, exercise_type,
                difficulty_level, score, accuracy, completion_time_seconds,
                user_answer, correct_answer
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id, session_id, exercise.category, exercise.type,
                exercise.difficulty, result.score, result.accuracy,
                result.completion_time, str(result.user_answer),
                str(exercise.correct_answer)
            )
        )

        logger.debug(
            "exercise_result_recorded",
            result_id=result_id,
            session_id=session_id,
            category=exercise.category,
            score=result.score
        )

    async def record_scenario_outcome(
        self,
        session_id: str,
        scenario: Dict[str, Any],
        outcome: ScenarioOutcome
    ):
        """Record a scenario outcome"""

        result_id = str(uuid.uuid4())

        # Prepare JSON data
        character_data = json.dumps([
            {
                'name': char['name'],
                'role': char['role'],
                'traits': char['personality_traits']
            } for char in scenario['characters']
        ])

        decisions = json.dumps(scenario['decision_history'])
        narrative_branches = json.dumps(scenario['narrative_branches'])

        self.db.execute(
            """
            INSERT INTO scenario_results (
                result_id, session_id, scenario_type, scenario_context,
                difficulty_level, character_data, decisions, narrative_branches,
                performance_score, decision_quality_score, completion_time_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id, session_id, scenario['type'], scenario['context'],
                scenario['difficulty'], character_data, decisions, narrative_branches,
                outcome.impact_score, outcome.decision_quality, outcome.turn_count
            )
        )

        logger.debug(
            "scenario_outcome_recorded",
            result_id=result_id,
            session_id=session_id,
            type=scenario['type'],
            score=outcome.decision_quality
        )

    async def get_progress_by_period(self, user_id: int, days: int) -> List[Dict[str, Any]]:
        """Get progress data for the specified period"""

        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        rows = self.db.fetchall(
            """
            SELECT date, cognitive_category,
                   AVG(average_score) as avg_score,
                   SUM(exercises_completed) as exercises,
                   SUM(scenarios_completed) as scenarios,
                   AVG(difficulty_level) as avg_difficulty
            FROM user_progress
            WHERE user_id = ? AND date >= ?
            GROUP BY date, cognitive_category
            ORDER BY date DESC
            """,
            (user_id, start_date)
        )

        return [
            {
                'date': row[0],
                'category': row[1],
                'avg_score': row[2],
                'exercises_completed': row[3],
                'scenarios_completed': row[4],
                'avg_difficulty': row[5]
            } for row in rows
        ]

    async def get_category_performance(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get performance breakdown by category"""

        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # Exercise performance by category
        exercise_stats = self.db.fetchall(
            """
            SELECT er.exercise_category,
                   COUNT(*) as total_exercises,
                   AVG(er.score) as avg_score,
                   AVG(er.accuracy) as avg_accuracy,
                   MAX(er.timestamp) as last_attempt
            FROM exercise_results er
            JOIN sessions s ON er.session_id = s.session_id
            WHERE s.user_id = ? AND er.timestamp >= ?
            GROUP BY er.exercise_category
            """,
            (user_id, start_date)
        )

        # Scenario performance by type
        scenario_stats = self.db.fetchall(
            """
            SELECT sr.scenario_type,
                   COUNT(*) as total_scenarios,
                   AVG(sr.performance_score) as avg_score,
                   AVG(sr.decision_quality_score) as avg_decision_quality,
                   MAX(sr.timestamp) as last_attempt
            FROM scenario_results sr
            JOIN sessions s ON sr.session_id = s.session_id
            WHERE s.user_id = ? AND sr.timestamp >= ?
            GROUP BY sr.scenario_type
            """,
            (user_id, start_date)
        )

        return {
            'exercise_categories': [
                {
                    'category': row[0],
                    'total_exercises': row[1],
                    'avg_score': row[2],
                    'avg_accuracy': row[3],
                    'last_attempt': row[4]
                } for row in exercise_stats
            ],
            'scenario_types': [
                {
                    'type': row[0],
                    'total_scenarios': row[1],
                    'avg_score': row[2],
                    'avg_decision_quality': row[3],
                    'last_attempt': row[4]
                } for row in scenario_stats
            ]
        }

    async def update_daily_progress(self, user_id: int, date: str, category: str, data: Dict[str, Any]):
        """Update or insert daily progress record"""

        # Check if record exists
        existing = self.db.fetchone(
            "SELECT progress_id FROM user_progress WHERE user_id = ? AND date = ? AND cognitive_category = ?",
            (user_id, date, category)
        )

        if existing:
            # Update existing
            self.db.execute(
                """
                UPDATE user_progress
                SET average_score = ?, exercises_completed = ?, scenarios_completed = ?, difficulty_level = ?
                WHERE user_id = ? AND date = ? AND cognitive_category = ?
                """,
                (
                    data['avg_score'], data['exercises'], data['scenarios'], data['difficulty'],
                    user_id, date, category
                )
            )
        else:
            # Insert new
            progress_id = str(uuid.uuid4())
            self.db.execute(
                """
                INSERT INTO user_progress (
                    progress_id, user_id, date, cognitive_category,
                    average_score, exercises_completed, scenarios_completed, difficulty_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    progress_id, user_id, date, category,
                    data['avg_score'], data['exercises'], data['scenarios'], data['difficulty']
                )
            )

    async def get_recent_exercise_results(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent exercise results for a user"""

        rows = self.db.fetchall(
            """
            SELECT er.*, s.session_type, s.difficulty_level as session_difficulty
            FROM exercise_results er
            JOIN sessions s ON er.session_id = s.session_id
            WHERE s.user_id = ?
            ORDER BY er.timestamp DESC
            LIMIT ?
            """,
            (user_id, limit)
        )

        return [self._exercise_result_to_dict(row) for row in rows]

    async def get_recent_scenario_results(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent scenario results for a user"""

        rows = self.db.fetchall(
            """
            SELECT sr.*, s.session_type, s.difficulty_level as session_difficulty
            FROM scenario_results sr
            JOIN sessions s ON sr.session_id = s.session_id
            WHERE s.user_id = ?
            ORDER BY sr.timestamp DESC
            LIMIT ?
            """,
            (user_id, limit)
        )

        return [self._scenario_result_to_dict(row) for row in rows]

    async def get_performance_trends(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Calculate performance trends over time"""

        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # Daily exercise scores
        exercise_trend = self.db.fetchall(
            """
            SELECT DATE(er.timestamp) as date, AVG(er.score) as avg_score, COUNT(*) as count
            FROM exercise_results er
            JOIN sessions s ON er.session_id = s.session_id
            WHERE s.user_id = ? AND er.timestamp >= ?
            GROUP BY DATE(er.timestamp)
            ORDER BY date
            """,
            (user_id, start_date)
        )

        # Daily scenario scores
        scenario_trend = self.db.fetchall(
            """
            SELECT DATE(sr.timestamp) as date, AVG(sr.performance_score) as avg_score, COUNT(*) as count
            FROM scenario_results sr
            JOIN sessions s ON sr.session_id = s.session_id
            WHERE s.user_id = ? AND sr.timestamp >= ?
            GROUP BY DATE(sr.timestamp)
            ORDER BY date
            """,
            (user_id, start_date)
        )

        return {
            'exercise_trend': [
                {'date': row[0], 'avg_score': row[1], 'count': row[2]}
                for row in exercise_trend
            ],
            'scenario_trend': [
                {'date': row[0], 'avg_score': row[1], 'count': row[2]}
                for row in scenario_trend
            ]
        }

    async def get_weakest_areas(self, user_id: int, days: int = 14) -> List[Dict[str, Any]]:
        """Identify weakest performing areas"""

        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # Exercise categories by average score (lowest first)
        weak_exercises = self.db.fetchall(
            """
            SELECT er.exercise_category, AVG(er.score) as avg_score, COUNT(*) as attempts
            FROM exercise_results er
            JOIN sessions s ON er.session_id = s.session_id
            WHERE s.user_id = ? AND er.timestamp >= ? AND attempts >= 3
            GROUP BY er.exercise_category
            ORDER BY avg_score ASC
            LIMIT 3
            """,
            (user_id, start_date)
        )

        # Scenario types by average score (lowest first)
        weak_scenarios = self.db.fetchall(
            """
            SELECT sr.scenario_type, AVG(sr.performance_score) as avg_score, COUNT(*) as attempts
            FROM scenario_results sr
            JOIN sessions s ON sr.session_id = s.session_id
            WHERE s.user_id = ? AND sr.timestamp >= ? AND attempts >= 2
            GROUP BY sr.scenario_type
            ORDER BY avg_score ASC
            LIMIT 2
            """,
            (user_id, start_date)
        )

        return {
            'weak_exercise_categories': [
                {'category': row[0], 'avg_score': row[1], 'attempts': row[2]}
                for row in weak_exercises
            ],
            'weak_scenario_types': [
                {'type': row[0], 'avg_score': row[1], 'attempts': row[2]}
                for row in weak_scenarios
            ]
        }

    async def _exercise_result_to_dict(self, row) -> Dict[str, Any]:
        """Convert exercise result row to dictionary"""

        return {
            'result_id': row[0],
            'session_id': row[1],
            'exercise_category': row[2],
            'exercise_type': row[3],
            'difficulty_level': row[4],
            'score': row[5],
            'accuracy': row[6],
            'completion_time_seconds': row[7],
            'timestamp': row[8],
            'user_answer': row[9],
            'correct_answer': row[10],
            'session_type': row[11],
            'session_difficulty': row[12]
        }

    async def _scenario_result_to_dict(self, row) -> Dict[str, Any]:
        """Convert scenario result row to dictionary"""

        return {
            'result_id': row[0],
            'session_id': row[1],
            'scenario_type': row[2],
            'scenario_context': row[3],
            'difficulty_level': row[4],
            'character_data': row[5],
            'decisions': row[6],
            'narrative_branches': row[7],
            'performance_score': row[8],
            'decision_quality_score': row[9],
            'completion_time_seconds': row[10],
            'timestamp': row[11],
            'session_type': row[12],
            'session_difficulty': row[13]
        }

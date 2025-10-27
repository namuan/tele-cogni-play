import uuid
import structlog
from typing import Dict, Any, Optional
from datetime import datetime
from cogniplay.engines.exercise_engine import ExerciseEngine
from cogniplay.engines.scenario_engine import ScenarioEngine
from cogniplay.core.difficulty_engine import DifficultyAdjustmentEngine
from cogniplay.data.repositories.session_repository import SessionRepository
from cogniplay.data.repositories.progress_repository import ProgressRepository

logger = structlog.get_logger()

class TrainingManager:
    """Orchestrates complete training sessions"""

    def __init__(
        self,
        exercise_engine: ExerciseEngine,
        scenario_engine: ScenarioEngine,
        difficulty_engine: DifficultyAdjustmentEngine,
        session_repository: SessionRepository,
        progress_repository: ProgressRepository
    ):
        self.exercise_engine = exercise_engine
        self.scenario_engine = scenario_engine
        self.difficulty_engine = difficulty_engine
        self.session_repo = session_repository
        self.progress_repo = progress_repository

    async def start_session(
        self,
        user_id: int,
        session_type: str,
        difficulty_level: Optional[int] = None
    ) -> Dict[str, Any]:
        """Start a new training session"""

        # Get current difficulty if not specified
        if difficulty_level is None:
            difficulty_level = await self.difficulty_engine.get_current_difficulty(user_id)

        # Create session
        session = await self.session_repo.create_session(
            user_id=user_id,
            session_type=session_type,
            difficulty_level=difficulty_level
        )

        logger.info(
            "training_session_started",
            session_id=session['session_id'],
            user_id=user_id,
            type=session_type,
            difficulty=difficulty_level
        )

        return session

    async def complete_session(
        self,
        session_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """Complete a training session and generate summary"""

        # Calculate final performance
        performance = await self._calculate_session_performance(session_id)

        # Complete session in database
        await self.session_repo.complete_session(
            session_id,
            performance.get('overall_avg_score')
        )

        # Update session stats
        await self.session_repo.update_session_stats(
            session_id,
            exercises_completed=performance['total_exercises'],
            scenarios_completed=performance['total_scenarios'],
            average_score=performance['overall_avg_score']
        )

        # Update user stats
        await self._update_user_stats(user_id, performance)

        # Generate summary
        summary = await self._generate_session_summary(session_id, performance)

        logger.info(
            "training_session_completed",
            session_id=session_id,
            user_id=user_id,
            exercises=performance['total_exercises'],
            scenarios=performance['total_scenarios'],
            avg_score=performance['overall_avg_score']
        )

        return summary

    async def _calculate_session_performance(self, session_id: str) -> Dict[str, Any]:
        """Calculate comprehensive session performance metrics"""

        # Get exercise results
        exercise_results = await self._get_session_exercise_results(session_id)
        scenario_results = await self._get_session_scenario_results(session_id)

        performance = {
            'total_exercises': len(exercise_results),
            'total_scenarios': len(scenario_results),
            'exercise_scores': [r['score'] for r in exercise_results],
            'scenario_scores': [r['performance_score'] for r in scenario_results],
            'avg_exercise_score': 0.0,
            'avg_scenario_score': 0.0,
            'overall_avg_score': 0.0,
            'completion_time_seconds': 0
        }

        # Calculate averages
        if exercise_results:
            performance['avg_exercise_score'] = (
                sum(r['score'] for r in exercise_results) / len(exercise_results)
            )

        if scenario_results:
            performance['avg_scenario_score'] = (
                sum(r['performance_score'] for r in scenario_results) / len(scenario_results)
            )

        # Overall score (weighted average)
        total_items = performance['total_exercises'] + performance['total_scenarios']
        if total_items > 0:
            performance['overall_avg_score'] = (
                (performance['avg_exercise_score'] * performance['total_exercises']) +
                (performance['avg_scenario_score'] * performance['total_scenarios'])
            ) / total_items

        # Calculate total time
        all_times = [r.get('completion_time_seconds', 0) for r in exercise_results]
        all_times.extend([r.get('completion_time_seconds', 0) for r in scenario_results])
        performance['completion_time_seconds'] = sum(all_times)

        return performance

    async def _update_user_stats(self, user_id: int, performance: Dict[str, Any]):
        """Update user's aggregate statistics"""

        # Update session count
        await self.session_repo.update_session_stats(
            session_id=None,  # Not needed for user stats
            exercises_completed=performance['total_exercises'],
            scenarios_completed=performance['total_scenarios']
        )

        # This would update user profile stats
        # For now, handled by individual repositories

    async def _generate_session_summary(
        self,
        session_id: str,
        performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive session summary"""

        session = await self.session_repo.get_session(session_id)
        duration_minutes = performance['completion_time_seconds'] // 60

        summary = {
            'session_id': session_id,
            'session_type': session['session_type'],
            'duration_seconds': performance['completion_time_seconds'],
            'duration_minutes': duration_minutes,
            'exercises_completed': performance['total_exercises'],
            'scenarios_completed': performance['total_scenarios'],
            'average_score': performance['overall_avg_score'],
            'avg_exercise_score': performance['avg_exercise_score'],
            'avg_scenario_score': performance['avg_scenario_score'],
            'recommendation': self._generate_session_recommendation(performance)
        }

        return summary

    def _generate_session_recommendation(self, performance: Dict[str, Any]) -> str:
        """Generate recommendation based on session performance"""

        score = performance['overall_avg_score']

        if score >= 90:
            return "Excellent session! You're performing at a high level. Try increasing difficulty for more challenge."
        elif score >= 80:
            return "Great work! Your performance is strong. Keep up the consistent practice."
        elif score >= 70:
            return "Good session! You're making progress. Focus on accuracy in your next session."
        elif score >= 60:
            return "Decent performance. Review the areas where you struggled and practice more."
        else:
            return "This session was challenging. Consider starting with easier exercises to build confidence."

    async def _get_session_exercise_results(self, session_id: str) -> list:
        """Get exercise results for session"""
        # This would query the database properly
        # For now, return empty list
        return []

    async def _get_session_scenario_results(self, session_id: str) -> list:
        """Get scenario results for session"""
        # This would query the database properly
        # For now, return empty list
        return []

    async def get_session_progress(self, session_id: str) -> Dict[str, Any]:
        """Get current progress for active session"""

        session = await self.session_repo.get_session(session_id)
        if not session:
            return {}

        # Get current stats
        exercise_count = session.get('exercises_completed', 0)
        scenario_count = session.get('scenarios_completed', 0)

        return {
            'session_id': session_id,
            'session_type': session['session_type'],
            'difficulty_level': session['difficulty_level'],
            'exercises_completed': exercise_count,
            'scenarios_completed': scenario_count,
            'total_completed': exercise_count + scenario_count,
            'start_time': session['start_time'],
            'is_active': session['end_time'] is None
        }

    async def cancel_session(self, session_id: str, user_id: int):
        """Cancel an active session"""

        # Mark as completed with minimal data
        await self.session_repo.complete_session(session_id, 0.0)

        logger.info(
            "training_session_cancelled",
            session_id=session_id,
            user_id=user_id
        )

    async def get_training_suggestions(self, user_id: int) -> Dict[str, Any]:
        """Get personalized training suggestions"""

        # Get recent performance
        recent_performance = await self.progress_repo.get_category_performance(user_id, 7)

        # Get current difficulty
        current_difficulty = await self.difficulty_engine.get_current_difficulty(user_id)

        suggestions = {
            'recommended_difficulty': current_difficulty,
            'suggested_categories': [],
            'focus_areas': [],
            'session_type': 'mixed'
        }

        # Suggest categories based on performance
        if recent_performance['exercise_categories']:
            # Suggest weaker categories
            weak_categories = sorted(
                recent_performance['exercise_categories'],
                key=lambda x: x['avg_score']
            )[:2]

            suggestions['suggested_categories'] = [
                cat['category'] for cat in weak_categories
            ]

        # Suggest session type
        exercise_count = sum(cat['total_exercises'] for cat in recent_performance['exercise_categories'])
        scenario_count = sum(cat['total_scenarios'] for cat in recent_performance['scenario_types'])

        if exercise_count > scenario_count * 2:
            suggestions['session_type'] = 'scenario_focus'
        elif scenario_count > exercise_count * 2:
            suggestions['session_type'] = 'exercise_focus'

        return suggestions

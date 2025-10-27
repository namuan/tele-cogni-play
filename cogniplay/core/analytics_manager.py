import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from cogniplay.data.repositories.progress_repository import ProgressRepository
from cogniplay.data.repositories.session_repository import SessionRepository
from cogniplay.data.models import ProgressReport, CategoryStats

logger = structlog.get_logger()

class AnalyticsManager:
    """Manages progress analytics and reporting"""

    def __init__(
        self,
        progress_repository: ProgressRepository,
        session_repository: SessionRepository
    ):
        self.progress_repo = progress_repository
        self.session_repo = session_repository

    async def calculate_session_performance(
        self,
        session_id: str
    ) -> Dict[str, float]:
        """Calculate metrics for completed session"""

        session = await self.session_repo.get_session(session_id)
        if not session:
            logger.warning("session_not_found", session_id=session_id)
            return {}

        # Get exercise results for this session
        exercise_results = await self._get_session_exercise_results(session_id)
        scenario_results = await self._get_session_scenario_results(session_id)

        # Calculate metrics
        metrics = {
            'total_exercises': len(exercise_results),
            'total_scenarios': len(scenario_results),
            'avg_exercise_score': 0.0,
            'avg_scenario_score': 0.0,
            'overall_avg_score': 0.0
        }

        if exercise_results:
            metrics['avg_exercise_score'] = sum(r['score'] for r in exercise_results) / len(exercise_results)

        if scenario_results:
            metrics['avg_scenario_score'] = sum(r['performance_score'] for r in scenario_results) / len(scenario_results)

        # Overall average (weighted by completion)
        total_items = metrics['total_exercises'] + metrics['total_scenarios']
        if total_items > 0:
            metrics['overall_avg_score'] = (
                (metrics['avg_exercise_score'] * metrics['total_exercises']) +
                (metrics['avg_scenario_score'] * metrics['total_scenarios'])
            ) / total_items

        return metrics

    async def generate_progress_report(
        self,
        user_id: int,
        days: int = 30
    ) -> ProgressReport:
        """Generate progress report for specified period"""

        # Get performance data
        category_performance = await self.progress_repo.get_category_performance(user_id, days)
        trends = await self.progress_repo.get_performance_trends(user_id, days)

        # Calculate overall trend
        overall_trend = self._calculate_trend(trends)

        # Identify strengths and weaknesses
        strongest_areas, weakest_areas = self._identify_areas(category_performance)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            category_performance,
            weakest_areas,
            overall_trend
        )

        # Build category stats
        categories = {}
        for cat_data in category_performance['exercise_categories']:
            categories[cat_data['category']] = CategoryStats(
                category=cat_data['category'],
                average_score=cat_data['avg_score'],
                exercises_completed=cat_data['total_exercises'],
                improvement_rate=self._calculate_improvement_rate(
                    trends['exercise_trend'],
                    cat_data['category']
                ),
                current_difficulty=await self._get_current_difficulty(user_id)
            )

        return ProgressReport(
            period_days=days,
            categories=categories,
            overall_trend=overall_trend,
            strongest_areas=strongest_areas,
            weakest_areas=weakest_areas,
            recommendations=recommendations
        )

    async def get_quick_stats(self, user_id: int) -> Dict[str, Any]:
        """Get quick performance statistics"""

        # Last 7 days
        week_data = await self.progress_repo.get_category_performance(user_id, 7)

        # Calculate averages
        total_exercises = sum(cat['total_exercises'] for cat in week_data['exercise_categories'])
        total_scenarios = sum(cat['total_scenarios'] for cat in week_data['scenario_types'])

        avg_exercise_score = 0
        if week_data['exercise_categories']:
            avg_exercise_score = sum(
                cat['avg_score'] * cat['total_exercises']
                for cat in week_data['exercise_categories']
            ) / total_exercises if total_exercises > 0 else 0

        avg_scenario_score = 0
        if week_data['scenario_types']:
            avg_scenario_score = sum(
                cat['avg_score'] * cat['total_scenarios']
                for cat in week_data['scenario_types']
            ) / total_scenarios if total_scenarios > 0 else 0

        # Best category
        best_category = "None"
        best_score = 0
        if week_data['exercise_categories']:
            best_cat = max(week_data['exercise_categories'], key=lambda x: x['avg_score'])
            best_category = best_cat['category']
            best_score = best_cat['avg_score']

        return {
            'avg_score_7d': avg_exercise_score,
            'exercises_7d': total_exercises,
            'scenarios_7d': total_scenarios,
            'best_category': best_category,
            'best_category_score': best_score
        }

    async def get_recommendations(self, user_id: int) -> List[str]:
        """Generate personalized training recommendations"""

        # Get recent performance
        performance = await self.progress_repo.get_category_performance(user_id, 14)
        weakest = await self.progress_repo.get_weakest_areas(user_id, 14)

        recommendations = []

        # Focus on weak areas
        if weakest['weak_exercise_categories']:
            weak_cat = weakest['weak_exercise_categories'][0]['category']
            recommendations.append(
                f"Focus on {weak_cat.replace('_', ' ')} exercises - practice regularly to improve"
            )

        # Balance training types
        exercise_count = sum(cat['total_exercises'] for cat in performance['exercise_categories'])
        scenario_count = sum(cat['total_scenarios'] for cat in performance['scenario_types'])

        if exercise_count > scenario_count * 2:
            recommendations.append("Try more role-playing scenarios to balance your training")
        elif scenario_count > exercise_count * 2:
            recommendations.append("Include more cognitive exercises in your sessions")

        # Difficulty adjustment
        current_difficulty = await self._get_current_difficulty(user_id)
        if current_difficulty == 1:
            recommendations.append("You're at beginner level - focus on building confidence with consistent practice")
        elif current_difficulty == 5:
            recommendations.append("You're at expert level - challenge yourself with complex scenarios")

        # Session frequency
        session_stats = await self.session_repo.get_user_session_stats(user_id)
        if session_stats['total_sessions'] < 5:
            recommendations.append("Train regularly (3-5 times per week) for best improvement")

        return recommendations[:3]  # Limit to 3 recommendations

    def _calculate_trend(self, trends: Dict[str, Any]) -> str:
        """Calculate overall performance trend"""

        exercise_trend = trends['exercise_trend']
        scenario_trend = trends['scenario_trend']

        if not exercise_trend and not scenario_trend:
            return 'stable'

        # Calculate trend direction
        def get_trend_direction(data_points):
            if len(data_points) < 2:
                return 0
            # Simple linear trend
            first_half = data_points[:len(data_points)//2]
            second_half = data_points[len(data_points)//2:]

            first_avg = sum(p['avg_score'] for p in first_half) / len(first_half) if first_half else 0
            second_avg = sum(p['avg_score'] for p in second_half) / len(second_half) if second_half else 0

            return second_avg - first_avg

        exercise_change = get_trend_direction(exercise_trend)
        scenario_change = get_trend_direction(scenario_trend)

        avg_change = (exercise_change + scenario_change) / 2

        if avg_change > 5:
            return 'improving'
        elif avg_change < -5:
            return 'declining'
        else:
            return 'stable'

    def _identify_areas(self, performance: Dict[str, Any]) -> tuple:
        """Identify strongest and weakest areas"""

        # Sort exercise categories by score
        exercise_cats = sorted(
            performance['exercise_categories'],
            key=lambda x: x['avg_score'],
            reverse=True
        )

        # Sort scenario types by score
        scenario_types = sorted(
            performance['scenario_types'],
            key=lambda x: x['avg_score'],
            reverse=True
        )

        strongest = []
        weakest = []

        # Top 2 strongest
        for cat in exercise_cats[:2]:
            strongest.append(cat['category'].replace('_', ' ').title())

        for scenario in scenario_types[:1]:  # Max 1 scenario type
            strongest.append(f"{scenario['type'].replace('_', ' ').title()} Scenarios")

        # Bottom 2 weakest
        for cat in exercise_cats[-2:]:
            weakest.append(cat['category'].replace('_', ' ').title())

        for scenario in scenario_types[-1:]:  # Max 1 scenario type
            weakest.append(f"{scenario['type'].replace('_', ' ').title()} Scenarios")

        return strongest[:3], weakest[:3]  # Limit to 3 each

    def _generate_recommendations(
        self,
        performance: Dict[str, Any],
        weakest_areas: List[str],
        trend: str
    ) -> List[str]:
        """Generate specific recommendations"""

        recommendations = []

        # Based on trend
        if trend == 'declining':
            recommendations.append("Your scores are trending down - focus on consistent practice")
        elif trend == 'stable':
            recommendations.append("Your performance is stable - try increasing difficulty or new challenge types")

        # Based on weak areas
        if weakest_areas:
            recommendations.append(f"Target improvement in: {', '.join(weakest_areas[:2])}")

        # Based on activity
        total_exercises = sum(cat['total_exercises'] for cat in performance['exercise_categories'])
        total_scenarios = sum(cat['total_scenarios'] for cat in performance['scenario_types'])

        if total_exercises < 10:
            recommendations.append("Complete more exercises to get better performance insights")
        if total_scenarios < 3:
            recommendations.append("Try more scenarios to develop decision-making skills")

        return recommendations[:3]

    def _calculate_improvement_rate(self, trend_data: List[Dict], category: str) -> float:
        """Calculate improvement rate for a category"""

        # Simplified: calculate slope of recent trend
        if len(trend_data) < 3:
            return 0.0

        # Use last 3 data points
        recent = trend_data[-3:]
        if len(recent) < 2:
            return 0.0

        # Simple slope calculation
        first_score = recent[0]['avg_score']
        last_score = recent[-1]['avg_score']
        days_diff = (datetime.fromisoformat(recent[-1]['date']) - datetime.fromisoformat(recent[0]['date'])).days

        if days_diff == 0:
            return 0.0

        return (last_score - first_score) / days_diff

    async def _get_current_difficulty(self, user_id: int) -> int:
        """Get user's current difficulty level"""
        # This would need to be implemented - for now return default
        return 1

    async def _get_session_exercise_results(self, session_id: str) -> List[Dict[str, Any]]:
        """Get exercise results for a session"""
        # This would query the database - simplified for now
        return []

    async def _get_session_scenario_results(self, session_id: str) -> List[Dict[str, Any]]:
        """Get scenario results for a session"""
        # This would query the database - simplified for now
        return []

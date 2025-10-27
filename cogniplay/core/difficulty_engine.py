import structlog
from typing import Optional, Dict, Any
from datetime import datetime
from cogniplay.data.repositories.difficulty_repository import DifficultyRepository
from cogniplay.data.repositories.user_repository import UserRepository

logger = structlog.get_logger()

class DifficultyAdjustmentEngine:
    """
    Manages dynamic difficulty adjustment based on user performance

    Rules:
    - 3 consecutive successes (≥90%): Level up
    - 3 consecutive failures (<50%): Level down
    - 5 difficulty levels total
    """

    # Constants
    MIN_LEVEL = 1
    MAX_LEVEL = 5
    SUCCESS_THRESHOLD = 90.0  # percentage
    FAILURE_THRESHOLD = 50.0  # percentage
    CONSECUTIVE_REQUIRED = 3

    def __init__(
        self,
        difficulty_repository: DifficultyRepository,
        user_repository: UserRepository
    ):
        self.difficulty_repo = difficulty_repository
        self.user_repo = user_repository

    async def process_result(
        self,
        user_id: int,
        accuracy: float,
        exercise_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process exercise/scenario result and adjust difficulty if needed

        Args:
            user_id: User identifier
            accuracy: Performance accuracy (0-100)
            exercise_type: Type of exercise/scenario

        Returns:
            Dict with adjustment info if level changed, None otherwise
        """

        # Get current tracking data
        tracking = await self.difficulty_repo.get_tracking(user_id)

        if not tracking:
            # Initialize tracking
            tracking = await self.difficulty_repo.create_tracking(user_id)

        # Determine result type
        if accuracy >= self.SUCCESS_THRESHOLD:
            result_type = 'success'
        elif accuracy < self.FAILURE_THRESHOLD:
            result_type = 'failure'
        else:
            result_type = 'neutral'

        # Update consecutive counters
        updated_tracking = self._update_tracking(tracking, result_type)

        # Check if adjustment needed
        adjustment = await self._check_adjustment(
            user_id,
            updated_tracking,
            exercise_type
        )

        # Save updated tracking
        await self.difficulty_repo.update_tracking(
            user_id,
            updated_tracking
        )

        if adjustment:
            logger.info(
                "difficulty_adjusted",
                user_id=user_id,
                old_level=adjustment['old_level'],
                new_level=adjustment['new_level'],
                reason=adjustment['reason']
            )

        return adjustment

    def _update_tracking(
        self,
        tracking: Dict[str, Any],
        result_type: str
    ) -> Dict[str, Any]:
        """Update consecutive success/failure counters"""

        tracking = tracking.copy()

        if result_type == 'success':
            tracking['consecutive_successes'] += 1
            tracking['consecutive_failures'] = 0
        elif result_type == 'failure':
            tracking['consecutive_failures'] += 1
            tracking['consecutive_successes'] = 0
        else:  # neutral
            # Don't reset counters for neutral results
            pass

        tracking['last_exercise_result'] = result_type
        tracking['last_updated'] = datetime.now()

        return tracking

    async def _check_adjustment(
        self,
        user_id: int,
        tracking: Dict[str, Any],
        exercise_type: str
    ) -> Optional[Dict[str, Any]]:
        """Check if difficulty level should be adjusted"""

        # Get current level
        user = await self.user_repo.get_user(user_id)
        if not user:
            logger.warning("user_not_found_for_adjustment", user_id=user_id)
            return None
        current_level = user['current_difficulty_level']

        adjustment = None

        # Check for level up
        if tracking['consecutive_successes'] >= self.CONSECUTIVE_REQUIRED:
            if current_level < self.MAX_LEVEL:
                new_level = current_level + 1
                adjustment = {
                    'old_level': current_level,
                    'new_level': new_level,
                    'direction': 'up',
                    'reason': f'{self.CONSECUTIVE_REQUIRED} consecutive successes',
                    'message': self._get_level_up_message(new_level)
                }

                # Update user level
                await self.user_repo.update_difficulty_level(
                    user_id,
                    new_level
                )

                # Reset counters
                tracking['consecutive_successes'] = 0
                tracking['consecutive_failures'] = 0

        # Check for level down
        elif tracking['consecutive_failures'] >= self.CONSECUTIVE_REQUIRED:
            if current_level > self.MIN_LEVEL:
                new_level = current_level - 1
                adjustment = {
                    'old_level': current_level,
                    'new_level': new_level,
                    'direction': 'down',
                    'reason': f'{self.CONSECUTIVE_REQUIRED} consecutive struggles',
                    'message': self._get_level_down_message(new_level)
                }

                # Update user level
                await self.user_repo.update_difficulty_level(
                    user_id,
                    new_level
                )

                # Reset counters
                tracking['consecutive_successes'] = 0
                tracking['consecutive_failures'] = 0

        return adjustment

    def _get_level_up_message(self, new_level: int) -> str:
        """Generate encouraging message for level increase"""

        messages = {
            2: "🎉 Great progress! Moving to Level 2. Challenges will become more engaging.",
            3: "🌟 Excellent work! Welcome to Level 3. You're showing real improvement!",
            4: "🚀 Outstanding! Level 4 unlocked. You're mastering complex challenges!",
            5: "👑 Incredible! Maximum difficulty reached. You're at expert level!"
        }

        return messages.get(
            new_level,
            f"Level increased to {new_level}!"
        )

    def _get_level_down_message(self, new_level: int) -> str:
        """Generate supportive message for level decrease"""

        messages = {
            1: "📚 No worries! We've adjusted to Level 1 to help you build confidence. You've got this!",
            2: "💪 Level adjusted to 2. Let's focus on strengthening fundamentals!",
            3: "🎯 Moving to Level 3. This pace will help you master the concepts better.",
            4: "✨ Level 4 still offers great challenges. Keep practicing!"
        }

        return messages.get(
            new_level,
            f"Level adjusted to {new_level} for optimal learning."
        )

    async def get_current_difficulty(self, user_id: int) -> int:
        """Get user's current difficulty level"""

        user = await self.user_repo.get_user(user_id)
        if not user:
            logger.warning("user_not_found_for_difficulty", user_id=user_id)
            return 1  # Default to level 1 for new users
        return user['current_difficulty_level']

    async def get_progress_towards_adjustment(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """Get progress towards next difficulty adjustment"""

        tracking = await self.difficulty_repo.get_tracking(user_id)
        current_level = await self.get_current_difficulty(user_id)

        if not tracking:
            return {
                'current_level': current_level,
                'consecutive_successes': 0,
                'consecutive_failures': 0,
                'next_adjustment': None
            }

        # Determine what's next
        next_adjustment = None

        if tracking['consecutive_successes'] > 0:
            remaining = self.CONSECUTIVE_REQUIRED - tracking['consecutive_successes']
            if current_level < self.MAX_LEVEL:
                next_adjustment = {
                    'type': 'level_up',
                    'current_streak': tracking['consecutive_successes'],
                    'required': self.CONSECUTIVE_REQUIRED,
                    'remaining': remaining
                }

        elif tracking['consecutive_failures'] > 0:
            remaining = self.CONSECUTIVE_REQUIRED - tracking['consecutive_failures']
            if current_level > self.MIN_LEVEL:
                next_adjustment = {
                    'type': 'level_down',
                    'current_streak': tracking['consecutive_failures'],
                    'required': self.CONSECUTIVE_REQUIRED,
                    'remaining': remaining
                }

        return {
            'current_level': current_level,
            'consecutive_successes': tracking['consecutive_successes'],
            'consecutive_failures': tracking['consecutive_failures'],
            'next_adjustment': next_adjustment
        }

    async def manual_adjustment(
        self,
        user_id: int,
        new_level: int,
        reason: str = "Manual adjustment"
    ) -> Dict[str, Any]:
        """Manually adjust difficulty level"""

        if not (self.MIN_LEVEL <= new_level <= self.MAX_LEVEL):
            raise ValueError(
                f"Level must be between {self.MIN_LEVEL} and {self.MAX_LEVEL}"
            )

        current_level = await self.get_current_difficulty(user_id)

        await self.user_repo.update_difficulty_level(user_id, new_level)

        # Reset tracking counters
        tracking = await self.difficulty_repo.get_tracking(user_id)
        if tracking:
            tracking['consecutive_successes'] = 0
            tracking['consecutive_failures'] = 0
            await self.difficulty_repo.update_tracking(user_id, tracking)

        logger.info(
            "manual_difficulty_adjustment",
            user_id=user_id,
            old_level=current_level,
            new_level=new_level,
            reason=reason
        )

        return {
            'old_level': current_level,
            'new_level': new_level,
            'direction': 'up' if new_level > current_level else 'down',
            'reason': reason,
            'message': f"Difficulty manually set to level {new_level}"
        }

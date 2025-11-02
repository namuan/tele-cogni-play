import asyncio
import structlog
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from cogniplay.config.settings import Settings
from cogniplay.config.logging_config import setup_comprehensive_logging, log_object_details
from cogniplay.database.connection import DatabaseConnection
from cogniplay.integrations.openrouter_client import OpenRouterClient, OpenRouterConfig
from cogniplay.integrations.character_generator import CharacterGenerator
from cogniplay.engines.exercise_engine import ExerciseEngine
from cogniplay.engines.scenario_engine import ScenarioEngine
from cogniplay.core.training_manager import TrainingManager
from cogniplay.core.analytics_manager import AnalyticsManager
from cogniplay.core.difficulty_engine import DifficultyAdjustmentEngine
from cogniplay.ui.components import (
    main_menu_keyboard,
    training_menu_keyboard,
    exercise_category_keyboard,
    scenario_type_keyboard,
    scenario_action_keyboard,
    error_main_menu_text,
    format_scenario_intro as ui_format_scenario_intro,
    format_actions_list,
)
from cogniplay.data.repositories import (
    UserRepository,
    SessionRepository,
    ProgressRepository,
    ExerciseRepository,
    DifficultyRepository,
    CharacterRepository
)

# Set up comprehensive logging with file output and stack traces
# This will be initialized after settings are loaded in main()
logger = structlog.get_logger()

# Conversation states
(
    MAIN_MENU,
    EXERCISE_CATEGORY,
    EXERCISE_ACTIVE,
    SCENARIO_TYPE,
    SCENARIO_ACTIVE,
    VIEW_PROGRESS
) = range(6)

class CogniPlayBot:
    """Main Telegram bot application"""

    def __init__(self, settings: Settings):
        self.settings = settings

        # Initialize database
        self.db = DatabaseConnection(settings.database_path)

        # Initialize repositories
        self.user_repo = UserRepository(self.db)
        self.session_repo = SessionRepository(self.db)
        self.progress_repo = ProgressRepository(self.db)
        self.exercise_repo = ExerciseRepository(self.db)
        self.difficulty_repo = DifficultyRepository(self.db)
        self.character_repo = CharacterRepository(self.db)

        # Initialize OpenRouter client
        openrouter_config = OpenRouterConfig(
            api_key=settings.openrouter_api_key,
            primary_model=settings.openrouter_primary_model,
            fallback_model=settings.openrouter_fallback_model
        )
        self.openrouter_client = OpenRouterClient(openrouter_config)

        # Initialize engines
        self.character_gen = CharacterGenerator(
            self.openrouter_client,
            self.character_repo
        )
        self.exercise_engine = ExerciseEngine(self.openrouter_client)
        self.scenario_engine = ScenarioEngine(
            self.openrouter_client,
            self.character_gen
        )

        # Initialize managers
        self.difficulty_engine = DifficultyAdjustmentEngine(
            self.difficulty_repo,
            self.user_repo
        )
        self.analytics_manager = AnalyticsManager(
            self.progress_repo,
            self.session_repo
        )
        self.training_manager = TrainingManager(
            self.exercise_engine,
            self.scenario_engine,
            self.difficulty_engine,
            self.session_repo,
            self.progress_repo
        )

        # Temporary state storage
        self.user_state = {}

    async def start_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle /start command"""

        user = update.effective_user

        # Check if authorized user
        if user.id != self.settings.telegram_user_id:
            await update.message.reply_text(
                "⛔ Sorry, this bot is private and not available for your use."
            )
            return ConversationHandler.END

        # Initialize or get user profile
        user_profile = await self.user_repo.get_or_create_user(user.id, user.username)

        welcome_text = f"""🧠 Welcome to CogniPlay! 🎮

Your personal cognitive training platform.

Current Difficulty Level: {user_profile['current_difficulty_level']}/5
Total Sessions: {user_profile['total_sessions']}

What would you like to do?"""

        reply_markup = main_menu_keyboard()

        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

        logger.info("user_started_bot", user_id=user.id)

        return MAIN_MENU

    async def train_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle /train command or callback"""

        query = update.callback_query
        if query:
            await query.answer()
            message = query.message
        else:
            message = update.message

        text = """🎯 Training Session

Choose your training mode:

1️⃣ Cognitive Exercises - Memory, logic, problem-solving challenges
2️⃣ Role-Playing Scenarios - Interactive AI character scenarios
3️⃣ Full Session - Both exercises and scenarios"""

        reply_markup = training_menu_keyboard()

        if query:
            await message.edit_text(text, reply_markup=reply_markup)
        else:
            await message.reply_text(text, reply_markup=reply_markup)

        return MAIN_MENU

    async def choose_exercise_category(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Let user choose exercise category"""

        query = update.callback_query
        await query.answer()

        # Start session (single user system - always use user_id=1)
        user_id = update.effective_user.id
        session = await self.training_manager.start_session(1, 'exercise_only')
        self.user_state[user_id] = {'session_id': session['session_id']}

        text = """🧩 Cognitive Exercises

Choose a category:"""

        reply_markup = exercise_category_keyboard()

        await query.message.edit_text(text, reply_markup=reply_markup)

        return EXERCISE_CATEGORY

    async def start_exercise(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Start a cognitive exercise"""

        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id

        # Get category from callback
        category_map = {
            'cat_memory': 'memory',
            'cat_logic': 'logic',
            'cat_problem_solving': 'problem_solving',
            'cat_pattern_recognition': 'pattern_recognition',
            'cat_attention': 'attention'
        }

        if query.data == 'cat_random':
            import random
            category = random.choice(list(category_map.values()))
        else:
            category = category_map.get(query.data, 'memory')

        # Get difficulty level
        difficulty = await self.difficulty_engine.get_current_difficulty(user_id)

        # Generate exercise
        exercise = await self.exercise_engine.generate_exercise(category, difficulty)

        # Store exercise in user state
        self.user_state[user_id]['current_exercise'] = exercise
        self.user_state[user_id]['exercise_start_time'] = asyncio.get_event_loop().time()

        # Send exercise
        text = f"""📝 Exercise #{self.user_state[user_id].get('exercises_completed', 0) + 1}

{exercise.question}

{f"⏱️ Time limit: {exercise.time_limit_seconds} seconds" if exercise.time_limit_seconds else ""}

Type your answer below:"""

        await query.message.edit_text(text)

        return EXERCISE_ACTIVE

    async def handle_exercise_answer(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Process user's exercise answer"""

        user_id = update.effective_user.id
        user_answer = update.message.text.strip()

        # Get current exercise
        exercise = self.user_state[user_id].get('current_exercise')
        if not exercise:
            await update.message.reply_text("No active exercise. Use /train to start.")
            return MAIN_MENU

        # Calculate completion time
        start_time = self.user_state[user_id].get('exercise_start_time', 0)
        completion_time = int(asyncio.get_event_loop().time() - start_time)

        # Validate answer
        result = await self.exercise_engine.validate_answer(
            exercise,
            user_answer,
            completion_time,
            hints_used=0
        )

        # Store result
        session_id = self.user_state[user_id]['session_id']
        await self.progress_repo.record_exercise_result(
            session_id,
            exercise,
            result
        )

        # Update difficulty tracking (single user system - always use user_id=1)
        adjustment = await self.difficulty_engine.process_result(
            1,
            result.accuracy,
            exercise.category
        )

        # Prepare feedback
        feedback = self._format_exercise_feedback(result, exercise)

        if adjustment:
            feedback += f"\n\n{adjustment['message']}"

        # Ask if user wants to continue
        keyboard = [
            [InlineKeyboardButton("✅ Next Exercise", callback_data='continue_exercise')],
            [InlineKeyboardButton("🎭 Switch to Scenario", callback_data='switch_scenario')],
            [InlineKeyboardButton("🏁 Finish Session", callback_data='finish_session')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(feedback, reply_markup=reply_markup)

        # Update exercise count
        self.user_state[user_id]['exercises_completed'] = \
            self.user_state[user_id].get('exercises_completed', 0) + 1

        return EXERCISE_CATEGORY

    def _format_exercise_feedback(self, result, exercise) -> str:
        """Format exercise result feedback"""

        if result.is_correct:
            emoji = "✅"
            verdict = "Correct!"
        else:
            emoji = "❌"
            verdict = "Incorrect"

        feedback = f"""{emoji} {verdict}

📊 Score: {result.score:.1f}/100
🎯 Accuracy: {result.accuracy:.1f}%
⏱️ Time: {result.completion_time}s

Your answer: {result.user_answer}
Correct answer: {exercise.correct_answer}"""

        return feedback

    async def choose_scenario_type(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Let user choose scenario type"""

        query = update.callback_query
        await query.answer()

        # Start session (single user system - always use user_id=1)
        user_id = update.effective_user.id
        session = await self.training_manager.start_session(1, 'scenario_only')
        self.user_state[user_id] = {'session_id': session['session_id']}

        text = """🎭 Role-Playing Scenarios

Choose a scenario type:"""

        reply_markup = scenario_type_keyboard()

        await query.message.edit_text(text, reply_markup=reply_markup)

        return SCENARIO_TYPE

    async def start_scenario(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Start a role-playing scenario"""

        query = update.callback_query
        await query.answer()
        await query.message.edit_text("🎬 Generating scenario... Please wait.")

        user_id = update.effective_user.id

        # Get scenario type from callback
        scenario_map = {
            'scen_negotiation': 'negotiation',
            'scen_problem_solving': 'problem_solving',
            'scen_social_interaction': 'social_interaction',
            'scen_leadership': 'leadership',
            'scen_creative_thinking': 'creative_thinking'
        }

        scenario_type = scenario_map.get(query.data, 'negotiation')

        # Get difficulty level
        difficulty = await self.difficulty_engine.get_current_difficulty(user_id)

        try:
            # Create scenario
            scenario = await self.scenario_engine.create_scenario(
                scenario_type,
                difficulty
            )

            # Store scenario in user state
            self.user_state[user_id]['current_scenario'] = scenario

            # Format scenario introduction
            text = self._format_scenario_intro(scenario)
            # Append full numbered options under the intro
            if scenario.get('available_actions'):
                text += "\n\nOptions:\n" + format_actions_list(scenario['available_actions'])

            # Create action buttons with concise labels
            reply_markup = scenario_action_keyboard(scenario['available_actions'], include_custom=True)

            await query.message.edit_text(text, reply_markup=reply_markup)

            return SCENARIO_ACTIVE

        except Exception as e:
            logger.error("scenario_creation_failed", error=str(e))
            # Inform user and present main menu again
            text = error_main_menu_text("❌ Failed to create scenario. Please try again.")
            reply_markup = main_menu_keyboard(show_settings=False)
            await query.message.edit_text(text, reply_markup=reply_markup)
            return MAIN_MENU

    def _format_scenario_intro(self, scenario) -> str:
        """Format scenario introduction (delegates to shared UI helper)"""
        return ui_format_scenario_intro(
            title=scenario['title'],
            context=scenario['context'],
            characters=scenario['characters'],
            initial_situation=scenario['initial_situation'],
        )

    async def handle_scenario_decision(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle user's scenario decision"""

        query = update.callback_query
        user_id = update.effective_user.id

        scenario = self.user_state[user_id].get('current_scenario')
        if not scenario:
            await query.answer("No active scenario")
            return MAIN_MENU

        if query.data == 'custom_action':
            await query.answer()
            await query.message.edit_text(
                "✍️ Type your custom action/response:\n\n"
                "(Or type /cancel to go back)"
            )
            self.user_state[user_id]['waiting_custom_action'] = True
            return SCENARIO_ACTIVE

        # Handle predefined action choice
        if query.data.startswith('action_'):
            action_index = int(query.data.split('_')[1])
            decision = scenario['available_actions'][action_index]
        else:
            await query.answer("Invalid action")
            return SCENARIO_ACTIVE

        await query.answer()
        await query.message.edit_text(
            f"🤔 Processing your decision...\n\n"
            f"Your action: {decision}"
        )

        # Process decision
        try:
            logger.debug(
                "calling_scenario_process_decision",
                scenario_id=scenario['id'],
                decision=decision
            )

            outcome = await self.scenario_engine.process_decision(
                scenario['id'],
                decision
            )

            # Log comprehensive details about the outcome object
            outcome_details = log_object_details(outcome, "outcome")
            logger.debug(
                "scenario_decision_processed_detailed",
                **outcome_details,
                scenario_id=scenario['id'],
                decision=decision
            )

            # Additional specific checks for the subscriptable issue
            logger.debug(
                "outcome_subscriptable_check",
                outcome_type=type(outcome).__name__,
                outcome_is_dict=isinstance(outcome, dict),
                outcome_is_dataclass=hasattr(outcome, '__dataclass_fields__'),
                has_next_actions_attr=hasattr(outcome, 'next_actions'),
                next_actions_value=getattr(outcome, 'next_actions', 'NO_ATTR') if hasattr(outcome, 'next_actions') else 'NO_ATTR',
                next_actions_type=type(getattr(outcome, 'next_actions', None)).__name__ if hasattr(outcome, 'next_actions') else 'NO_ATTR'
            )

            # Store outcome
            session_id = self.user_state[user_id]['session_id']
            await self.progress_repo.record_scenario_outcome(
                session_id,
                scenario,
                outcome
            )

            # Update difficulty tracking (single user system - always use user_id=1)
            adjustment = await self.difficulty_engine.process_result(
                1,
                outcome.decision_quality,
                'scenario'
            )

            # Format response
            text = self._format_scenario_response(outcome, scenario)

            if adjustment:
                text += f"\n\n📈 {adjustment['message']}"

            if outcome.is_complete:
                # Scenario completed
                conclusion_text = self._format_scenario_conclusion(
                    outcome.conclusion if hasattr(outcome, 'conclusion') and outcome.conclusion else {}
                )
                text += f"\n\n{conclusion_text}"

                keyboard = [
                    [InlineKeyboardButton("🎯 Another Scenario", callback_data='mode_scenario')],
                    [InlineKeyboardButton("🧩 Do Exercises", callback_data='mode_exercise')],
                    [InlineKeyboardButton("🏁 Finish Session", callback_data='finish_session')]
                ]

                # Clean up scenario
                self.scenario_engine.cleanup_scenario(scenario['id'])
            else:
                # Continue scenario
                keyboard = []
                
                # Log before attempting subscript access
                logger.debug(
                    "before_next_actions_access",
                    outcome_type=type(outcome).__name__,
                    has_next_actions=hasattr(outcome, 'next_actions'),
                    next_actions_value=getattr(outcome, 'next_actions', 'NO_ATTR') if hasattr(outcome, 'next_actions') else 'NO_ATTR'
                )
                
                try:
                    # Use attribute access instead of subscript access
                    next_actions = outcome.next_actions if hasattr(outcome, 'next_actions') else []
                    logger.debug(
                        "next_actions_retrieved",
                        next_actions_count=len(next_actions) if next_actions else 0,
                        next_actions_type=type(next_actions).__name__
                    )
                except Exception as e:
                    logger.error(
                        "next_actions_access_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        outcome_details=log_object_details(outcome, "outcome_error")
                    )
                    # Fallback: create empty actions list
                    next_actions = []

                # Append full numbered options to the message
                if next_actions:
                    text += "\n\nOptions:\n" + format_actions_list(next_actions)

                # Build concise-labeled keyboard and add End button
                markup = scenario_action_keyboard(next_actions, include_custom=True)
                keyboard = [list(row) for row in markup.inline_keyboard]
                keyboard.append([InlineKeyboardButton("🛑 End Scenario", callback_data='end_scenario')])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(text, reply_markup=reply_markup)

            return SCENARIO_ACTIVE if not outcome.is_complete else MAIN_MENU

        except Exception as e:
            logger.error("scenario_decision_failed", error=str(e))
            await query.message.edit_text(
                "❌ Error processing decision. Please try again."
            )
            return SCENARIO_ACTIVE

    async def handle_custom_action(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle custom action text from user"""

        user_id = update.effective_user.id

        if not self.user_state[user_id].get('waiting_custom_action'):
            return await self.handle_exercise_answer(update, context)

        custom_action = update.message.text.strip()

        if custom_action.lower() == '/cancel':
            await update.message.reply_text("Cancelled. Choose a predefined action:")
            self.user_state[user_id]['waiting_custom_action'] = False
            return SCENARIO_ACTIVE

        self.user_state[user_id]['waiting_custom_action'] = False

        # Process custom action
        scenario = self.user_state[user_id].get('current_scenario')

        await update.message.reply_text(
            f"🤔 Processing your action...\n\n"
            f"Your action: {custom_action}"
        )

        try:
            outcome = await self.scenario_engine.process_decision(
                scenario['id'],
                custom_action
            )

            # Log comprehensive details about the outcome object
            outcome_details = log_object_details(outcome, "custom_action_outcome")
            logger.debug(
                "custom_action_processed_detailed",
                **outcome_details,
                scenario_id=scenario['id'],
                custom_action=custom_action
            )

            # Store outcome
            session_id = self.user_state[user_id]['session_id']
            await self.progress_repo.record_scenario_outcome(
                session_id,
                scenario,
                outcome
            )

            # Update difficulty (single user system - always use user_id=1)
            adjustment = await self.difficulty_engine.process_result(
                1,
                outcome.decision_quality,
                'scenario'
            )

            # Format response
            text = self._format_scenario_response(outcome, scenario)

            if adjustment:
                text += f"\n\n📈 {adjustment['message']}"

            if outcome.is_complete:
                conclusion_text = self._format_scenario_conclusion(
                    outcome.conclusion if hasattr(outcome, 'conclusion') and outcome.conclusion else {}
                )
                text += f"\n\n{conclusion_text}"

                keyboard = [
                    [InlineKeyboardButton("🎯 Another Scenario", callback_data='mode_scenario')],
                    [InlineKeyboardButton("🧩 Do Exercises", callback_data='mode_exercise')],
                    [InlineKeyboardButton("🏁 Finish Session", callback_data='finish_session')]
                ]

                self.scenario_engine.cleanup_scenario(scenario['id'])
            else:
                # Continue scenario
                keyboard = []
                
                # Log before attempting subscript access
                logger.debug(
                    "before_custom_next_actions_access",
                    outcome_type=type(outcome).__name__,
                    has_next_actions=hasattr(outcome, 'next_actions'),
                    next_actions_value=getattr(outcome, 'next_actions', 'NO_ATTR') if hasattr(outcome, 'next_actions') else 'NO_ATTR'
                )
                
                try:
                    # Use attribute access instead of subscript access
                    next_actions = outcome.next_actions if hasattr(outcome, 'next_actions') else []
                    logger.debug(
                        "custom_next_actions_retrieved",
                        next_actions_count=len(next_actions) if next_actions else 0,
                        next_actions_type=type(next_actions).__name__
                    )
                except Exception as e:
                    logger.error(
                        "custom_next_actions_access_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        outcome_details=log_object_details(outcome, "custom_outcome_error")
                    )
                    # Fallback: create empty actions list
                    next_actions = []

                # Append full numbered options to the message
                if next_actions:
                    text += "\n\nOptions:\n" + format_actions_list(next_actions)

                # Build concise-labeled keyboard and add End button
                markup = scenario_action_keyboard(next_actions, include_custom=True)
                keyboard = [list(row) for row in markup.inline_keyboard]
                keyboard.append([InlineKeyboardButton("🛑 End Scenario", callback_data='end_scenario')])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup)

            return SCENARIO_ACTIVE if not outcome.is_complete else MAIN_MENU

        except Exception as e:
            logger.error("custom_action_failed", error=str(e))
            await update.message.reply_text("❌ Error processing action. Try again.")
            return SCENARIO_ACTIVE

    def _format_scenario_response(self, outcome, scenario) -> str:
        """Format scenario outcome response"""

        character_name = scenario['characters'][0]['name']

        text = f"""🎭 Turn {outcome.turn_count}

💬 {character_name}:
{outcome.ai_response}

📖 {outcome.narrative_update}

📊 Decision Quality: {outcome.decision_quality:.1f}/100

What do you do next?"""

        return text

    def _format_scenario_conclusion(self, conclusion) -> str:
        """Format scenario conclusion"""

        if not conclusion:
            return "🎬 Scenario completed!"

        text = f"""🎬 Scenario Complete!

📊 Performance Summary:
• Total Turns: {conclusion['total_turns']}
• Average Score: {conclusion['average_score']:.1f}/100
• Grade: {conclusion['performance_grade']}

{conclusion['summary']}"""

        return text

    async def show_progress(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Show progress analytics"""

        query = update.callback_query
        if query:
            await query.answer()
            message = query.message
        else:
            message = update.message

        user_id = update.effective_user.id

        # Ask for time period
        text = "📊 Progress Analytics\n\nChoose time period:"

        keyboard = [
            [InlineKeyboardButton("📅 Last 7 Days", callback_data='progress_7')],
            [InlineKeyboardButton("📅 Last 30 Days", callback_data='progress_30')],
            [InlineKeyboardButton("📅 Last 90 Days", callback_data='progress_90')],
            [InlineKeyboardButton("📅 All Time", callback_data='progress_all')],
            [InlineKeyboardButton("« Back", callback_data='back_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if query:
            await message.edit_text(text, reply_markup=reply_markup)
        else:
            await message.reply_text(text, reply_markup=reply_markup)

        return VIEW_PROGRESS

    async def display_progress_report(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Display detailed progress report"""

        query = update.callback_query
        await query.answer()
        await query.message.edit_text("📊 Generating report...")

        user_id = update.effective_user.id

        # Parse period from callback
        period_map = {
            'progress_7': 7,
            'progress_30': 30,
            'progress_90': 90,
            'progress_all': None
        }

        days = period_map.get(query.data, 30)

        try:
            # Generate report
            report = await self.analytics_manager.generate_progress_report(
                user_id,
                days
            )

            # Format report
            text = self._format_progress_report(report, days)

            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data=query.data)],
                [InlineKeyboardButton("« Back", callback_data='progress')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')

            return VIEW_PROGRESS

        except Exception as e:
            logger.error("progress_report_failed", error=str(e))
            await query.message.edit_text(
                "❌ Failed to generate report. Please try again."
            )
            return MAIN_MENU

    def _format_progress_report(self, report, days) -> str:
        """Format progress report for display"""

        period_text = f"Last {days} Days" if days else "All Time"

        text = f"""📊 <b>Progress Report - {period_text}</b>

<b>Overall Trend:</b> {report.overall_trend.title()} {'📈' if report.overall_trend == 'improving' else '📊' if report.overall_trend == 'stable' else '📉'}

<b>Performance by Category:</b>
"""

        for category, stats in report.categories.items():
            emoji_map = {
                'memory': '🧠',
                'logic': '🔍',
                'problem_solving': '💡',
                'pattern_recognition': '🎨',
                'attention': '👁️'
            }
            emoji = emoji_map.get(category, '📝')

            trend = '↗️' if stats.improvement_rate > 0 else '↘️' if stats.improvement_rate < 0 else '➡️'

            text += f"\n{emoji} <b>{category.replace('_', ' ').title()}</b>\n"
            text += f"  Score: {stats.average_score:.1f}/100 {trend}\n"
            text += f"  Completed: {stats.exercises_completed}\n"
            text += f"  Level: {stats.current_difficulty}/5\n"

        text += f"\n<b>💪 Strengths:</b>\n"
        for strength in report.strongest_areas:
            text += f"  • {strength}\n"

        text += f"\n<b>🎯 Areas for Improvement:</b>\n"
        for weakness in report.weakest_areas:
            text += f"  • {weakness}\n"

        text += f"\n<b>📝 Recommendations:</b>\n"
        for rec in report.recommendations[:3]:
            text += f"  • {rec}\n"

        return text

    async def finish_session(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Finish training session and show summary"""

        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        session_id = self.user_state[user_id].get('session_id')

        if not session_id:
            await query.message.edit_text("No active session.")
            return MAIN_MENU

        await query.message.edit_text("🏁 Completing session...")

        try:
            # Complete session
            summary = await self.training_manager.complete_session(session_id, user_id)

            # Format summary
            text = self._format_session_summary(summary)

            keyboard = [
                [InlineKeyboardButton("🎯 New Session", callback_data='train')],
                [InlineKeyboardButton("📊 View Progress", callback_data='progress')],
                [InlineKeyboardButton("🏠 Main Menu", callback_data='back_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.edit_text(text, reply_markup=reply_markup)

            # Clean up user state
            self.user_state[user_id] = {}

            return MAIN_MENU

        except Exception as e:
            logger.error("session_completion_failed", error=str(e))
            await query.message.edit_text("❌ Error completing session.")
            return MAIN_MENU

    def _format_session_summary(self, summary) -> str:
        """Format session completion summary"""

        duration_minutes = summary['duration_minutes']

        text = f"""🏁 <b>Session Complete!</b>

⏱️ Duration: {duration_minutes} minutes
🧩 Exercises: {summary['exercises_completed']}
🎭 Scenarios: {summary['scenarios_completed']}

📊 <b>Performance:</b>
Average Score: {summary['average_score']:.1f}/100
{'🎉 Great job!' if summary['average_score'] >= 80 else '💪 Keep practicing!' if summary['average_score'] >= 60 else '📚 Focus on improvement!'}

<b>Next Steps:</b>
{summary['recommendation']}"""

        return text

    async def help_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Show help information"""

        query = update.callback_query
        if query:
            await query.answer()
            message = query.message
        else:
            message = update.message

        text = """❓ <b>CogniPlay Help</b>

<b>Available Commands:</b>
/start - Start the bot and see main menu
/train - Start a training session
/progress - View your progress analytics
/stats - Quick performance statistics
/difficulty - View current difficulty level
/help - Show this help message

<b>How It Works:</b>

🧩 <b>Cognitive Exercises</b>
Choose from 5 categories of brain training exercises. Your performance is tracked and difficulty adjusts automatically.

🎭 <b>Role-Playing Scenarios</b>
Interact with AI characters in realistic situations. Practice decision-making and problem-solving in context.

📊 <b>Progress Tracking</b>
View detailed analytics on your improvement over time. Get personalized recommendations.

⚙️ <b>Adaptive Difficulty</b>
• 3 successes (≥90%) → Level up
• 3 failures (<50%) → Level down
• 5 difficulty levels (1-5)

<b>Tips for Success:</b>
• Train regularly for best results
• Try all exercise categories
• Take time to think through scenarios
• Review your progress weekly"""

        keyboard = [[InlineKeyboardButton("« Back", callback_data='back_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if query:
            await message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

        return MAIN_MENU

    async def stats_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Show quick statistics"""

        user_id = update.effective_user.id

        try:
            user_profile = await self.user_repo.get_user(user_id)
            quick_stats = await self.analytics_manager.get_quick_stats(user_id)

            text = f"""📈 <b>Quick Statistics</b>

<b>Profile:</b>
Difficulty Level: {user_profile['current_difficulty_level']}/5
Total Sessions: {user_profile['total_sessions']}
Exercises Completed: {user_profile['total_exercises_completed']}
Scenarios Completed: {user_profile['total_scenarios_completed']}

<b>Recent Performance (7 days):</b>
Average Score: {quick_stats['avg_score_7d']:.1f}/100
Sessions: {quick_stats['exercises_7d'] + quick_stats['scenarios_7d']}
Streak: Keep training regularly!

<b>Best Category:</b>
{quick_stats['best_category'].replace('_', ' ').title()} ({quick_stats['best_category_score']:.1f}/100)"""

            keyboard = [
                [InlineKeyboardButton("📊 Detailed Progress", callback_data='progress')],
                [InlineKeyboardButton("« Back", callback_data='back_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

            return MAIN_MENU

        except Exception as e:
            logger.error("stats_display_failed", error=str(e))
            await update.message.reply_text("❌ Failed to load statistics.")
            return MAIN_MENU

    async def difficulty_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Show difficulty information"""

        user_id = update.effective_user.id

        try:
            progress = await self.difficulty_engine.get_progress_towards_adjustment(user_id)

            text = f"""⚙️ <b>Difficulty Level</b>

Current Level: {progress['current_level']}/5

<b>Progress Tracking:</b>
Consecutive Successes: {progress['consecutive_successes']}/3
Consecutive Failures: {progress['consecutive_failures']}/3
"""

            if progress['next_adjustment']:
                adj = progress['next_adjustment']
                text += f"\n<b>Next Adjustment:</b>\n"
                text += f"{adj['type'].replace('_', ' ').title()}\n"
                text += f"Progress: {adj['current_streak']}/{adj['required']}\n"
                text += f"Remaining: {adj['remaining']} more\n"
            else:
                text += "\n<i>Keep training to trigger adjustments!</i>\n"

            text += f"""
<b>Adjustment Rules:</b>
• 3 successes (≥90%) → Level up
• 3 failures (<50%) → Level down

<i>Difficulty adjusts automatically based on your performance.</i>"""

            keyboard = [[InlineKeyboardButton("« Back", callback_data='back_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

            return MAIN_MENU

        except Exception as e:
            logger.error("difficulty_display_failed", error=str(e))
            await update.message.reply_text("❌ Failed to load difficulty info.")
            return MAIN_MENU

    async def cancel_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Cancel current operation"""

        user_id = update.effective_user.id
        self.user_state[user_id] = {}

        await update.message.reply_text(
            "Operation cancelled. Use /start to return to main menu."
        )

        return ConversationHandler.END

    async def error_handler(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle errors with extensive logging and full stack trace"""

        import traceback
        import sys

        # Get full stack trace
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))

        # Log comprehensive error information
        logger.error(
            "update_error_detailed",
            error=str(context.error),
            error_type=type(context.error).__name__,
            update_id=update.update_id if update else None,
            user_id=update.effective_user.id if update and update.effective_user else None,
            chat_id=update.effective_chat.id if update and update.effective_chat else None,
            message_text=update.effective_message.text if update and update.effective_message else None,
            full_traceback=tb_str
        )

        # Check for specific error types
        if isinstance(context.error, TypeError) and "object dict can't be used in 'await' expression" in str(context.error):
            logger.error(
                "async_await_error_detected",
                message="Dictionary being awaited instead of coroutine - check async method calls",
                error_details=str(context.error)
            )
        elif isinstance(context.error, TypeError) and "object is not subscriptable" in str(context.error):
            logger.error(
                "none_subscript_error_detected",
                message="Trying to access subscript on None object - check for None values before accessing dict/list",
                error_details=str(context.error),
                full_traceback=tb_str
            )

        # Send user-friendly error message
        error_message = "❌ An error occurred. Please try again or use /start to restart."
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(error_message)
            except Exception as reply_error:
                logger.error("failed_to_send_error_message", reply_error=str(reply_error))

    def run(self):
        """Run the bot"""

        # Create application
        application = Application.builder().token(
            self.settings.telegram_bot_token
        ).build()

        # Define conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start_command)],
            states={
                MAIN_MENU: [
                    CallbackQueryHandler(self.train_command, pattern='^train$'),
                    CallbackQueryHandler(self.choose_exercise_category, pattern='^mode_exercise$'),
                    CallbackQueryHandler(self.choose_scenario_type, pattern='^mode_scenario$'),
                    CallbackQueryHandler(self.show_progress, pattern='^progress$'),
                    CallbackQueryHandler(self.help_command, pattern='^help$'),
                    CallbackQueryHandler(self.finish_session, pattern='^finish_session$'),
                ],
                EXERCISE_CATEGORY: [
                    CallbackQueryHandler(self.start_exercise, pattern='^cat_'),
                    CallbackQueryHandler(self.choose_exercise_category, pattern='^continue_exercise$'),
                    CallbackQueryHandler(self.choose_scenario_type, pattern='^switch_scenario$'),
                    CallbackQueryHandler(self.train_command, pattern='^back_train$'),
                ],
                EXERCISE_ACTIVE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_exercise_answer),
                ],
                SCENARIO_TYPE: [
                    CallbackQueryHandler(self.start_scenario, pattern='^scen_'),
                    CallbackQueryHandler(self.train_command, pattern='^back_train$'),
                ],
                SCENARIO_ACTIVE: [
                    CallbackQueryHandler(self.handle_scenario_decision, pattern='^action_'),
                    CallbackQueryHandler(self.handle_scenario_decision, pattern='^custom_action$'),
                    CallbackQueryHandler(self.finish_session, pattern='^end_scenario$'),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_custom_action),
                ],
                VIEW_PROGRESS: [
                    CallbackQueryHandler(self.display_progress_report, pattern='^progress_'),
                    CallbackQueryHandler(self.show_progress, pattern='^progress$'),
                    CallbackQueryHandler(self.start_command, pattern='^back_main$'),
                ],
            },
            fallbacks=[
                CommandHandler('cancel', self.cancel_command),
                CommandHandler('start', self.start_command),
            ],
        )

        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler('train', self.train_command))
        application.add_handler(CommandHandler('progress', self.show_progress))
        application.add_handler(CommandHandler('stats', self.stats_command))
        application.add_handler(CommandHandler('difficulty', self.difficulty_command))
        application.add_handler(CommandHandler('help', self.help_command))

        # Add error handler
        application.add_error_handler(self.error_handler)

        # Start bot
        logger.info("bot_starting")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point"""

    # Load settings
    settings = Settings()
    
    # Initialize logging with settings
    setup_comprehensive_logging(log_level=settings.log_level, log_file="cogniplay_debug.log")

    # Initialize and run bot
    bot = CogniPlayBot(settings)
    bot.run()


if __name__ == '__main__':
    main()

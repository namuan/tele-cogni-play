from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

@dataclass
class UserProfile:
    user_id: int
    telegram_user_id: int
    telegram_username: Optional[str]
    created_at: datetime
    last_active: datetime
    current_difficulty_level: int
    total_sessions: int
    total_exercises_completed: int
    total_scenarios_completed: int

@dataclass
class Session:
    session_id: str
    user_id: int
    session_type: str  # 'full', 'exercise_only', 'scenario_only'
    start_time: datetime
    end_time: Optional[datetime]
    difficulty_level: int
    exercises_completed: int
    scenarios_completed: int
    average_score: Optional[float]

@dataclass
class ExerciseResult:
    result_id: str
    session_id: str
    exercise_category: str
    exercise_type: str
    difficulty_level: int
    score: float
    accuracy: float
    completion_time_seconds: int
    timestamp: datetime
    user_answer: str
    correct_answer: str

@dataclass
class ScenarioResult:
    result_id: str
    session_id: str
    scenario_type: str
    scenario_context: str
    difficulty_level: int
    character_data: str  # JSON
    decisions: str  # JSON
    narrative_branches: str  # JSON
    performance_score: float
    decision_quality_score: float
    completion_time_seconds: int
    timestamp: datetime

@dataclass
class UserProgress:
    progress_id: str
    user_id: int
    date: str  # YYYY-MM-DD
    cognitive_category: str
    average_score: float
    exercises_completed: int
    scenarios_completed: int
    difficulty_level: int

@dataclass
class DifficultyTracking:
    tracking_id: int
    user_id: int
    consecutive_successes: int
    consecutive_failures: int
    last_exercise_result: str  # 'success', 'failure', 'neutral'
    last_updated: datetime

@dataclass
class AICharacterMemory:
    character_id: str
    character_name: str
    personality_traits: str  # JSON
    communication_style: str
    background: str
    interaction_history: str  # JSON
    created_at: datetime
    last_used: Optional[datetime]

@dataclass
class ExerciseTemplate:
    template_id: str
    category: str
    exercise_type: str
    difficulty_level: int
    template_data: str  # JSON
    description: str
    active: bool

# Business Logic Models

@dataclass
class Exercise:
    id: str
    category: str
    type: str
    difficulty: int
    question: str
    correct_answer: Any
    options: Optional[List[str]]
    time_limit_seconds: Optional[int]
    hints: Optional[List[str]]

@dataclass
class ExerciseResult:
    exercise_id: str
    user_answer: Any
    is_correct: bool
    score: float
    accuracy: float
    completion_time: int
    hints_used: int

@dataclass
class AICharacter:
    id: str
    name: str
    role: str
    personality_traits: Dict[str, str]
    background: str

@dataclass
class Scenario:
    id: str
    type: str
    context: str
    difficulty: int
    characters: List[AICharacter]
    initial_situation: str
    available_actions: List[str]
    current_situation: str
    decision_history: List[Dict]
    narrative_branches: List[str]
    start_time: str
    turn_count: int
    is_complete: bool

@dataclass
class ScenarioOutcome:
    scenario_id: str
    user_decision: str
    ai_response: str
    narrative_update: str
    narrative_branch: str
    impact_score: float
    decision_quality: float
    is_complete: bool
    next_actions: Optional[List[str]]
    turn_count: int

@dataclass
class ProgressReport:
    period_days: int
    categories: Dict[str, 'CategoryStats']
    overall_trend: str  # 'improving', 'stable', 'declining'
    strongest_areas: List[str]
    weakest_areas: List[str]
    recommendations: List[str]

@dataclass
class CategoryStats:
    category: str
    average_score: float
    exercises_completed: int
    improvement_rate: float
    current_difficulty: int

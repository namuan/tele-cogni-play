import sqlite3
import structlog
from pathlib import Path
from typing import Optional, Any
from contextlib import contextmanager

logger = structlog.get_logger()

class DatabaseConnection:
    """SQLite database connection manager"""

    def __init__(self, db_path: str = "./data/cogniplay.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Configure SQLite for better performance
        self._connection: Optional[sqlite3.Connection] = None
        self._setup_connection()

    def _setup_connection(self):
        """Initialize database connection with optimizations"""
        self._connection = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,  # Allow multi-threading
            isolation_level=None  # Auto-commit mode
        )

        # Enable WAL mode for better concurrency
        self._connection.execute("PRAGMA journal_mode=WAL;")
        self._connection.execute("PRAGMA synchronous=NORMAL;")
        self._connection.execute("PRAGMA cache_size=-64000;")  # 64MB cache
        self._connection.execute("PRAGMA temp_store=MEMORY;")
        self._connection.execute("PRAGMA foreign_keys=ON;")

        # Create tables if they don't exist
        self._create_tables()

        logger.info("database_connected", path=str(self.db_path))

    def _create_tables(self):
        """Create database schema"""

        schema_sql = """
        -- User Profile (Single User)
        CREATE TABLE IF NOT EXISTS user_profile (
            user_id INTEGER PRIMARY KEY CHECK (user_id = 1),
            telegram_user_id BIGINT UNIQUE NOT NULL,
            telegram_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_difficulty_level INTEGER DEFAULT 1 CHECK (current_difficulty_level BETWEEN 1 AND 5),
            total_sessions INTEGER DEFAULT 0,
            total_exercises_completed INTEGER DEFAULT 0,
            total_scenarios_completed INTEGER DEFAULT 0
        );

        -- Sessions
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES user_profile(user_id),
            session_type TEXT CHECK (session_type IN ('full', 'exercise_only', 'scenario_only')),
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            difficulty_level INTEGER,
            exercises_completed INTEGER DEFAULT 0,
            scenarios_completed INTEGER DEFAULT 0,
            average_score REAL
        );

        -- Exercise Results
        CREATE TABLE IF NOT EXISTS exercise_results (
            result_id TEXT PRIMARY KEY,
            session_id TEXT REFERENCES sessions(session_id),
            exercise_category TEXT NOT NULL,
            exercise_type TEXT NOT NULL,
            difficulty_level INTEGER,
            score REAL CHECK (score BETWEEN 0 AND 100),
            accuracy REAL CHECK (accuracy BETWEEN 0 AND 100),
            completion_time_seconds INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_answer TEXT,
            correct_answer TEXT
        );

        -- Scenario Results
        CREATE TABLE IF NOT EXISTS scenario_results (
            result_id TEXT PRIMARY KEY,
            session_id TEXT REFERENCES sessions(session_id),
            scenario_type TEXT NOT NULL,
            scenario_context TEXT,
            difficulty_level INTEGER,
            character_data TEXT, -- JSON: [{name, traits, role}]
            decisions TEXT, -- JSON: [{decision, impact, timestamp}]
            narrative_branches TEXT, -- JSON: [branch_ids]
            performance_score REAL CHECK (performance_score BETWEEN 0 AND 100),
            decision_quality_score REAL,
            completion_time_seconds INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- User Progress (Aggregated Daily)
        CREATE TABLE IF NOT EXISTS user_progress (
            progress_id TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES user_profile(user_id),
            date DATE NOT NULL,
            cognitive_category TEXT NOT NULL,
            average_score REAL,
            exercises_completed INTEGER,
            scenarios_completed INTEGER,
            difficulty_level INTEGER,
            UNIQUE(date, cognitive_category)
        );

        -- Difficulty Tracking (Consecutive Performance)
        CREATE TABLE IF NOT EXISTS difficulty_tracking (
            tracking_id INTEGER PRIMARY KEY CHECK (tracking_id = 1),
            user_id INTEGER REFERENCES user_profile(user_id),
            consecutive_successes INTEGER DEFAULT 0,
            consecutive_failures INTEGER DEFAULT 0,
            last_exercise_result TEXT CHECK (last_exercise_result IN ('success', 'failure', 'neutral')),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- AI Character Memory (For Consistency)
        CREATE TABLE IF NOT EXISTS ai_character_memory (
            character_id TEXT PRIMARY KEY,
            character_name TEXT NOT NULL,
            personality_traits TEXT, -- JSON
            communication_style TEXT,
            background TEXT,
            interaction_history TEXT, -- JSON: [{timestamp, scenario_id, user_action, response}]
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP
        );

        -- Exercise Templates
        CREATE TABLE IF NOT EXISTS exercise_templates (
            template_id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            exercise_type TEXT NOT NULL,
            difficulty_level INTEGER,
            template_data TEXT, -- JSON: exercise configuration
            description TEXT,
            active BOOLEAN DEFAULT 1
        );

        -- Indexes for Performance
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_exercise_results_session ON exercise_results(session_id);
        CREATE INDEX IF NOT EXISTS idx_exercise_results_category ON exercise_results(exercise_category);
        CREATE INDEX IF NOT EXISTS idx_scenario_results_session ON scenario_results(session_id);
        CREATE INDEX IF NOT EXISTS idx_user_progress_date ON user_progress(date);
        CREATE INDEX IF NOT EXISTS idx_user_progress_category ON user_progress(cognitive_category);
        """

        self._connection.executescript(schema_sql)
        logger.info("database_schema_created")

    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        cursor = self._connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor"""
        return self._connection.execute(query, params)

    def executemany(self, query: str, params_list: list) -> sqlite3.Cursor:
        """Execute a query with multiple parameter sets"""
        return self._connection.executemany(query, params_list)

    def fetchone(self, query: str, params: tuple = ()) -> Optional[tuple]:
        """Execute query and fetch one result"""
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query: str, params: tuple = ()) -> list:
        """Execute query and fetch all results"""
        cursor = self.execute(query, params)
        return cursor.fetchall()

    def commit(self):
        """Commit current transaction"""
        self._connection.commit()

    def rollback(self):
        """Rollback current transaction"""
        self._connection.rollback()

    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            logger.info("database_connection_closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

import uuid
import json
import structlog
from typing import Optional, Dict, Any, List
from cogniplay.database.connection import DatabaseConnection

logger = structlog.get_logger()

class ExerciseRepository:
    """Repository for exercise templates and operations"""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def get_exercise_by_category_and_level(self, category: str, difficulty_level: int) -> Optional[Dict[str, Any]]:
        """Get a random active exercise template by category and difficulty"""

        row = self.db.fetchone(
            """
            SELECT * FROM exercise_templates
            WHERE category = ? AND difficulty_level = ? AND active = 1
            ORDER BY RANDOM() LIMIT 1
            """,
            (category, difficulty_level)
        )

        if row:
            return self._row_to_dict(row)
        return None

    async def get_random_exercise(self, category: Optional[str] = None, difficulty_level: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get a random exercise, optionally filtered by category/difficulty"""

        query = "SELECT * FROM exercise_templates WHERE active = 1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if difficulty_level:
            query += " AND difficulty_level = ?"
            params.append(difficulty_level)

        query += " ORDER BY RANDOM() LIMIT 1"

        row = self.db.fetchone(query, tuple(params))

        if row:
            return self._row_to_dict(row)
        return None

    async def validate_answer(self, exercise_template: Dict[str, Any], user_answer: Any) -> bool:
        """Validate user's answer against exercise template"""

        # This would contain validation logic based on exercise type
        # For now, return True (validation happens in exercise engine)
        return True

    async def save_exercise_template(self, template: Dict[str, Any]) -> str:
        """Save a new exercise template"""

        template_id = str(uuid.uuid4())

        self.db.execute(
            """
            INSERT INTO exercise_templates (
                template_id, category, exercise_type, difficulty_level,
                template_data, description, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_id,
                template['category'],
                template['exercise_type'],
                template['difficulty_level'],
                json.dumps(template['template_data']),
                template.get('description', ''),
                template.get('active', True)
            )
        )

        logger.info(
            "exercise_template_saved",
            template_id=template_id,
            category=template['category'],
            type=template['exercise_type']
        )

        return template_id

    async def update_exercise_template(self, template_id: str, updates: Dict[str, Any]):
        """Update an existing exercise template"""

        # Build dynamic update query
        set_parts = []
        params = []

        for key, value in updates.items():
            if key == 'template_data':
                set_parts.append("template_data = ?")
                params.append(json.dumps(value))
            else:
                set_parts.append(f"{key} = ?")
                params.append(value)

        if set_parts:
            query = f"UPDATE exercise_templates SET {', '.join(set_parts)} WHERE template_id = ?"
            params.append(template_id)
            self.db.execute(query, tuple(params))

            logger.info("exercise_template_updated", template_id=template_id)

    async def deactivate_exercise_template(self, template_id: str):
        """Deactivate an exercise template"""

        self.db.execute(
            "UPDATE exercise_templates SET active = 0 WHERE template_id = ?",
            (template_id,)
        )

        logger.info("exercise_template_deactivated", template_id=template_id)

    async def get_exercise_templates(self, category: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get exercise templates, optionally filtered"""

        query = "SELECT * FROM exercise_templates"
        params = []

        conditions = []
        if category:
            conditions.append("category = ?")
            params.append(category)

        if active_only:
            conditions.append("active = 1")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY category, difficulty_level"

        rows = self.db.fetchall(query, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    async def get_exercise_stats(self) -> Dict[str, Any]:
        """Get statistics about exercise templates"""

        # Count by category
        category_counts = self.db.fetchall(
            """
            SELECT category, COUNT(*) as count
            FROM exercise_templates
            WHERE active = 1
            GROUP BY category
            """
        )

        # Count by difficulty
        difficulty_counts = self.db.fetchall(
            """
            SELECT difficulty_level, COUNT(*) as count
            FROM exercise_templates
            WHERE active = 1
            GROUP BY difficulty_level
            """
        )

        return {
            'total_templates': sum(row[1] for row in category_counts),
            'by_category': {row[0]: row[1] for row in category_counts},
            'by_difficulty': {row[0]: row[1] for row in difficulty_counts}
        }

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary"""

        return {
            'template_id': row[0],
            'category': row[1],
            'exercise_type': row[2],
            'difficulty_level': row[3],
            'template_data': json.loads(row[4]) if row[4] else {},
            'description': row[5],
            'active': bool(row[6])
        }

import uuid
import json
import structlog
from typing import Optional, Dict, Any, List
from datetime import datetime
from cogniplay.database.connection import DatabaseConnection

logger = structlog.get_logger()

class CharacterRepository:
    """Repository for AI character memory and operations"""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def save_character(self, character: Dict[str, Any]):
        """Save or update a character"""

        character_id = character['id']

        # Check if character exists
        existing = self.db.fetchone(
            "SELECT character_id FROM ai_character_memory WHERE character_id = ?",
            (character_id,)
        )

        if existing:
            # Update existing
            self.db.execute(
                """
                UPDATE ai_character_memory
                SET character_name = ?, personality_traits = ?, communication_style = ?,
                    background = ?, last_used = CURRENT_TIMESTAMP
                WHERE character_id = ?
                """,
                (
                    character['name'],
                    json.dumps(character['personality_traits']),
                    character.get('communication_style', ''),
                    character.get('background', ''),
                    character_id
                )
            )
        else:
            # Insert new
            self.db.execute(
                """
                INSERT INTO ai_character_memory (
                    character_id, character_name, personality_traits,
                    communication_style, background, interaction_history
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    character_id,
                    character['name'],
                    json.dumps(character['personality_traits']),
                    character.get('communication_style', ''),
                    character.get('background', ''),
                    json.dumps(character.get('interaction_history', []))
                )
            )

        logger.debug("character_saved", character_id=character_id, name=character['name'])

    async def get_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get character by ID"""

        row = self.db.fetchone(
            "SELECT * FROM ai_character_memory WHERE character_id = ?",
            (character_id,)
        )

        if row:
            return self._row_to_dict(row)
        return None

    async def get_characters_by_scenario_type(self, scenario_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get characters suitable for a scenario type"""

        # For now, return recent characters (could be enhanced with tagging)
        rows = self.db.fetchall(
            """
            SELECT * FROM ai_character_memory
            ORDER BY last_used DESC
            LIMIT ?
            """,
            (limit,)
        )

        return [self._row_to_dict(row) for row in rows]

    async def add_interaction(self, character_id: str, interaction: Dict[str, Any]):
        """Add an interaction to character's memory"""

        character = await self.get_character(character_id)
        if not character:
            logger.warning("character_not_found_for_interaction", character_id=character_id)
            return

        # Get current interactions
        interactions = character.get('interaction_history', [])

        # Add new interaction
        interactions.append(interaction)

        # Keep only last 10 interactions to prevent bloat
        if len(interactions) > 10:
            interactions = interactions[-10:]

        # Update database
        self.db.execute(
            """
            UPDATE ai_character_memory
            SET interaction_history = ?, last_used = CURRENT_TIMESTAMP
            WHERE character_id = ?
            """,
            (json.dumps(interactions), character_id)
        )

        logger.debug("interaction_added", character_id=character_id, interaction_count=len(interactions))

    async def update_character_memory(self, character_id: str, memory_updates: Dict[str, Any]):
        """Update character's memory with new information"""

        # Build dynamic update
        set_parts = []
        params = []

        for key, value in memory_updates.items():
            if key in ['personality_traits', 'interaction_history']:
                set_parts.append(f"{key} = ?")
                params.append(json.dumps(value))
            else:
                set_parts.append(f"{key} = ?")
                params.append(value)

        if set_parts:
            query = f"UPDATE ai_character_memory SET {', '.join(set_parts)} WHERE character_id = ?"
            params.append(character_id)
            self.db.execute(query, tuple(params))

            logger.debug("character_memory_updated", character_id=character_id)

    async def get_character_stats(self) -> Dict[str, Any]:
        """Get statistics about stored characters"""

        total_characters = self.db.fetchone(
            "SELECT COUNT(*) FROM ai_character_memory",
            ()
        )[0]

        # Characters by communication style
        style_counts = self.db.fetchall(
            """
            SELECT communication_style, COUNT(*) as count
            FROM ai_character_memory
            GROUP BY communication_style
            """
        )

        # Recent activity
        recent_count = self.db.fetchone(
            """
            SELECT COUNT(*) FROM ai_character_memory
            WHERE last_used > datetime('now', '-7 days')
            """,
            ()
        )[0]

        return {
            'total_characters': total_characters,
            'by_communication_style': {row[0]: row[1] for row in style_counts},
            'recently_used': recent_count
        }

    async def cleanup_old_characters(self, days_old: int = 90):
        """Remove characters that haven't been used recently"""

        cutoff_date = (datetime.now().timestamp() - days_old * 24 * 3600)

        deleted_count = self.db.execute(
            "DELETE FROM ai_character_memory WHERE last_used < ?",
            (cutoff_date,)
        ).rowcount

        if deleted_count > 0:
            logger.info("old_characters_cleaned_up", deleted_count=deleted_count)

        return deleted_count

    async def search_characters(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search characters by name or background"""

        search_pattern = f"%{query}%"

        rows = self.db.fetchall(
            """
            SELECT * FROM ai_character_memory
            WHERE character_name LIKE ? OR background LIKE ?
            ORDER BY last_used DESC
            LIMIT ?
            """,
            (search_pattern, search_pattern, limit)
        )

        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary"""

        return {
            'character_id': row[0],
            'character_name': row[1],
            'personality_traits': json.loads(row[2]) if row[2] else {},
            'communication_style': row[3],
            'background': row[4],
            'interaction_history': json.loads(row[5]) if row[5] else [],
            'created_at': row[6],
            'last_used': row[7]
        }

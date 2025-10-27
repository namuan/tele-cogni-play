import uuid
import structlog
from typing import Dict, List, Any, Optional
from datetime import datetime
from cogniplay.database.connection import DatabaseConnection

logger = structlog.get_logger()

class CharacterGenerator:
    """Generate and manage AI characters for scenarios"""

    def __init__(
        self,
        openrouter_client,
        character_repository: DatabaseConnection
    ):
        self.client = openrouter_client
        self.repository = character_repository

        # Character templates by role
        self.templates = {
            'negotiation': [
                {'role': 'Business Partner', 'archetype': 'pragmatic'},
                {'role': 'Client', 'archetype': 'demanding'},
                {'role': 'Vendor', 'archetype': 'competitive'}
            ],
            'problem_solving': [
                {'role': 'Team Lead', 'archetype': 'collaborative'},
                {'role': 'Technical Expert', 'archetype': 'analytical'},
                {'role': 'Stakeholder', 'archetype': 'concerned'}
            ],
            'social_interaction': [
                {'role': 'Colleague', 'archetype': 'friendly'},
                {'role': 'Supervisor', 'archetype': 'professional'},
                {'role': 'Peer', 'archetype': 'casual'}
            ],
            'leadership': [
                {'role': 'Team Member', 'archetype': 'supportive'},
                {'role': 'Difficult Employee', 'archetype': 'resistant'},
                {'role': 'Senior Manager', 'archetype': 'authoritative'}
            ],
            'creative_thinking': [
                {'role': 'Creative Partner', 'archetype': 'innovative'},
                {'role': 'Critic', 'archetype': 'skeptical'},
                {'role': 'Client', 'archetype': 'open_minded'}
            ]
        }

        # Personality trait options
        self.trait_options = {
            'temperament': [
                'Friendly', 'Professional', 'Challenging',
                'Neutral', 'Enthusiastic', 'Reserved'
            ],
            'communication_style': [
                'Direct', 'Diplomatic', 'Technical',
                'Casual', 'Formal', 'Concise'
            ],
            'emotional_state': [
                'Calm', 'Stressed', 'Enthusiastic',
                'Skeptical', 'Optimistic', 'Frustrated'
            ],
            'goals': [
                'Cooperative', 'Competitive', 'Hidden Agenda',
                'Helpful', 'Self-interested', 'Neutral'
            ]
        }

    async def create_character(
        self,
        scenario_type: str,
        difficulty: int,
        specific_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create new AI character for scenario

        Args:
            scenario_type: Type of scenario (negotiation, problem_solving, etc.)
            difficulty: Scenario difficulty level (1-5)
            specific_role: Optional specific role to create

        Returns:
            Character dictionary with personality and background
        """

        # Select character template
        templates = self.templates.get(scenario_type, [])
        if not templates:
            templates = self.templates['social_interaction']

        if specific_role:
            template = next(
                (t for t in templates if t['role'] == specific_role),
                templates[0]
            )
        else:
            import random
            template = random.choice(templates)

        # Generate personality based on difficulty
        personality = self._generate_personality(
            template['archetype'],
            difficulty
        )

        # Create character profile
        character = {
            'id': str(uuid.uuid4()),
            'name': self._generate_name(template['role']),
            'role': template['role'],
            'personality_traits': personality,
            'background': self._generate_background(
                template['role'],
                personality,
                difficulty
            ),
            'created_at': datetime.now().isoformat()
        }

        # Store in database for consistency
        await self.repository.save_character(character)

        logger.info(
            "character_created",
            character_id=character['id'],
            role=character['role'],
            scenario_type=scenario_type
        )

        return character

    def _generate_personality(
        self,
        archetype: str,
        difficulty: int
    ) -> Dict[str, str]:
        """Generate personality traits based on archetype and difficulty"""

        import random

        # Base traits by archetype
        archetype_traits = {
            'pragmatic': {
                'temperament': 'Professional',
                'communication_style': 'Direct',
                'emotional_state': 'Calm',
                'goals': 'Self-interested'
            },
            'demanding': {
                'temperament': 'Challenging',
                'communication_style': 'Direct',
                'emotional_state': 'Stressed',
                'goals': 'Competitive'
            },
            'collaborative': {
                'temperament': 'Friendly',
                'communication_style': 'Diplomatic',
                'emotional_state': 'Enthusiastic',
                'goals': 'Cooperative'
            },
            'analytical': {
                'temperament': 'Reserved',
                'communication_style': 'Technical',
                'emotional_state': 'Calm',
                'goals': 'Helpful'
            },
            'friendly': {
                'temperament': 'Friendly',
                'communication_style': 'Casual',
                'emotional_state': 'Optimistic',
                'goals': 'Cooperative'
            }
        }

        base_traits = archetype_traits.get(
            archetype,
            archetype_traits['pragmatic']
        )

        # Add complexity based on difficulty
        if difficulty >= 3:
            # Higher difficulty: add unpredictability
            trait_keys = list(base_traits.keys())
            random_key = random.choice(trait_keys)
            base_traits[random_key] = random.choice(
                self.trait_options[random_key]
            )

        if difficulty >= 4:
            # Very high difficulty: hidden agenda
            base_traits['goals'] = 'Hidden Agenda'

        return base_traits

    def _generate_name(self, role: str) -> str:
        """Generate appropriate name for character"""

        import random

        first_names = [
            'Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey',
            'Riley', 'Avery', 'Quinn', 'Sage', 'Drew',
            'Sam', 'Jamie', 'Chris', 'Pat', 'Robin'
        ]

        last_names = [
            'Chen', 'Patel', 'Johnson', 'Williams', 'Garcia',
            'Martinez', 'Kim', 'Lee', 'Brown', 'Davis'
        ]

        return f"{random.choice(first_names)} {random.choice(last_names)}"

    def _generate_background(
        self,
        role: str,
        personality: Dict[str, str],
        difficulty: int
    ) -> str:
        """Generate character background story"""

        backgrounds = {
            'Business Partner': [
                "Has been in the industry for 10 years and values efficiency.",
                "Recently promoted and eager to prove themselves.",
                "Experienced negotiator with strong network connections."
            ],
            'Team Lead': [
                "Manages a team of 8 and focuses on collaboration.",
                "New to leadership but highly technical.",
                "Veteran leader known for developing talent."
            ],
            'Client': [
                "Running a startup and needs quick solutions.",
                "Represents a Fortune 500 company with high standards.",
                "Small business owner watching every dollar."
            ]
        }

        import random
        role_backgrounds = backgrounds.get(
            role,
            ["Professional with relevant experience."]
        )

        return random.choice(role_backgrounds)

    async def get_character(self, character_id: str) -> Optional[Dict]:
        """Retrieve character from database"""
        return await self.repository.get_character(character_id)

    async def update_character_memory(
        self,
        character_id: str,
        interaction: Dict[str, Any]
    ):
        """Update character's interaction history"""

        character = await self.get_character(character_id)
        if not character:
            logger.warning(
                "character_not_found",
                character_id=character_id
            )
            return

        # Add to interaction history
        await self.repository.add_interaction(character_id, interaction)

        logger.debug(
            "character_memory_updated",
            character_id=character_id,
            interaction_count=len(character.get('interaction_history', []))
        )

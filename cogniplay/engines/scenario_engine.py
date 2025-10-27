import uuid
import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime
from cogniplay.integrations.openrouter_client import OpenRouterClient
from cogniplay.integrations.character_generator import CharacterGenerator
from cogniplay.data.models import ScenarioOutcome

logger = structlog.get_logger()

class ScenarioEngine:
    """Manage role-playing scenarios with AI characters"""

    def __init__(
        self,
        openrouter_client: OpenRouterClient,
        character_generator: CharacterGenerator
    ):
        self.client = openrouter_client
        self.character_gen = character_generator

        # Active scenarios cache (in-memory)
        self.active_scenarios: Dict[str, Dict] = {}

    async def create_scenario(
        self,
        scenario_type: str,
        difficulty: int,
        user_preferences: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create new role-playing scenario

        Args:
            scenario_type: Type of scenario (negotiation, problem_solving, etc.)
            difficulty: Difficulty level (1-5)
            user_preferences: Optional user preferences

        Returns:
            Scenario dictionary with characters and initial situation
        """

        # Generate scenario structure via AI
        scenario_data = await self.client.generate_scenario(
            scenario_type,
            difficulty,
            user_preferences
        )

        # Create characters
        characters = []
        for char_data in scenario_data.get('characters', []):
            character = {
                'id': str(uuid.uuid4()),
                'name': char_data['name'],
                'role': char_data['role'],
                'personality_traits': char_data['personality_traits'],
                'background': char_data.get('background', ''),
                'interaction_history': []
            }

            # Save character to database
            await self.character_gen.repository.save_character(character)
            characters.append(character)

        # Build scenario object
        scenario = {
            'id': str(uuid.uuid4()),
            'type': scenario_type,
            'difficulty': difficulty,
            'context': scenario_data.get('context', ''),
            'title': scenario_data.get('title', f'{scenario_type.title()} Scenario'),
            'characters': characters,
            'initial_situation': scenario_data.get('initial_situation', ''),
            'current_situation': scenario_data.get('initial_situation', ''),
            'available_actions': scenario_data.get('initial_options', []),
            'decision_history': [],
            'narrative_branches': [],
            'start_time': datetime.now().isoformat(),
            'turn_count': 0,
            'is_complete': False
        }

        # Store in active scenarios cache
        self.active_scenarios[scenario['id']] = scenario

        logger.info(
            "scenario_created",
            scenario_id=scenario['id'],
            type=scenario_type,
            difficulty=difficulty,
            character_count=len(characters)
        )

        return scenario

    async def process_decision(
        self,
        scenario_id: str,
        decision: str,
        decision_index: Optional[int] = None
    ) -> ScenarioOutcome:
        """
        Process user decision and generate AI response

        Args:
            scenario_id: Scenario identifier
            decision: User's decision/action text
            decision_index: Optional index if choosing from options

        Returns:
            ScenarioOutcome with AI response and next actions
        """

        scenario = self.active_scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        # Select primary character to respond
        character = scenario['characters'][0]  # Primary character

        # Build context for AI
        context = {
            'situation': scenario['current_situation'],
            'interaction_history': character['interaction_history'][-3:],  # Last 3 turns
            'scenario_type': scenario['type'],
            'difficulty': scenario['difficulty']
        }

        # Get AI response
        ai_response = await self.client.generate_character_response(
            character,
            decision,
            context
        )

        # Update interaction history
        interaction = {
            'turn': scenario['turn_count'] + 1,
            'user_action': decision,
            'ai_response': ai_response['response'],
            'narrative': ai_response['narrative'],
            'timestamp': datetime.now().isoformat()
        }

        character['interaction_history'].append(interaction)
        await self.character_gen.update_character_memory(
            character['id'],
            interaction
        )

        # Evaluate decision quality
        decision_quality = await self._evaluate_decision(
            scenario,
            decision,
            ai_response
        )

        # Update scenario state
        scenario['turn_count'] += 1
        scenario['current_situation'] = ai_response['narrative']
        scenario['available_actions'] = ai_response.get('options', [])
        scenario['decision_history'].append({
            'decision': decision,
            'quality': decision_quality,
            'impact': ai_response['narrative']
        })

        # Determine branch
        branch_id = f"branch_{scenario['turn_count']}"
        scenario['narrative_branches'].append(branch_id)

        # Check if scenario should conclude
        should_conclude = (
            scenario['turn_count'] >= 5 + scenario['difficulty'] or
            len(ai_response.get('options', [])) == 0
        )

        outcome = ScenarioOutcome(
            scenario_id=scenario_id,
            user_decision=decision,
            ai_response=ai_response['response'],
            narrative_update=ai_response['narrative'],
            narrative_branch=branch_id,
            impact_score=decision_quality,
            decision_quality=decision_quality,
            is_complete=should_conclude,
            next_actions=ai_response.get('options', []),
            turn_count=scenario['turn_count']
        )

        if should_conclude:
            scenario['is_complete'] = True
            outcome.conclusion = await self.get_scenario_conclusion(scenario_id)

        logger.info(
            "decision_processed",
            scenario_id=scenario_id,
            turn=scenario['turn_count'],
            quality=decision_quality,
            is_complete=should_conclude
        )

        return outcome

    async def _evaluate_decision(
        self,
        scenario: Dict,
        decision: str,
        ai_response: Dict
    ) -> float:
        """
        Evaluate quality of user's decision

        Returns:
            Score from 0-100
        """

        # Use AI to evaluate decision quality
        evaluation_prompt = [{
            'role': 'system',
            'content': f"""Evaluate the quality of this decision in a {scenario['type']} scenario.

Context: {scenario['current_situation']}
User's decision: {decision}
Outcome: {ai_response['narrative']}

Rate the decision on a scale of 0-100 based on:
- Appropriateness for the situation
- Strategic thinking
- Communication effectiveness
- Problem-solving approach
- Consideration of consequences

Respond with ONLY a number between 0-100."""
        }]

        try:
            response = await self.client._make_request(
                model=self.client.config.fallback_model,  # Use cheaper model
                messages=evaluation_prompt,
                temperature=0.3,
                max_tokens=10
            )

            score_text = response['choices'][0]['message']['content'].strip()
            score = float(''.join(c for c in score_text if c.isdigit() or c == '.'))
            score = max(0, min(100, score))  # Clamp to 0-100

        except Exception as e:
            logger.warning("decision_evaluation_failed", error=str(e))
            # Fallback: simple heuristic
            score = 70.0  # Neutral score

        return score

    async def get_scenario_conclusion(
        self,
        scenario_id: str
    ) -> Dict[str, Any]:
        """
        Generate final scenario assessment and feedback

        Returns:
            Conclusion with overall performance analysis
        """

        scenario = self.active_scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        # Calculate overall performance
        decision_scores = [
            d['quality'] for d in scenario['decision_history']
        ]
        average_score = sum(decision_scores) / len(decision_scores) if decision_scores else 0

        # Build summary prompt
        summary_prompt = [{
            'role': 'system',
            'content': f"""Provide a brief conclusion for this {scenario['type']} scenario.

Scenario: {scenario['title']}
Turns: {scenario['turn_count']}
Decision History: {len(scenario['decision_history'])} decisions made
Average Decision Quality: {average_score:.1f}/100

Provide:
1. A 2-3 sentence outcome summary
2. Key strengths shown (1-2 points)
3. Areas for improvement (1-2 points)
4. One actionable tip

Keep it concise and constructive."""
        }]

        try:
            response = await self.client._make_request(
                model=self.client.config.primary_model,
                messages=summary_prompt,
                temperature=0.7,
                max_tokens=300
            )

            conclusion_text = response['choices'][0]['message']['content']

        except Exception as e:
            logger.error("conclusion_generation_failed", error=str(e))
            conclusion_text = f"Scenario completed with an average decision quality of {average_score:.1f}/100."

        conclusion = {
            'scenario_id': scenario_id,
            'total_turns': scenario['turn_count'],
            'average_score': average_score,
            'decision_count': len(scenario['decision_history']),
            'narrative_branches': len(scenario['narrative_branches']),
            'summary': conclusion_text,
            'performance_grade': self._get_grade(average_score)
        }

        logger.info(
            "scenario_concluded",
            scenario_id=scenario_id,
            average_score=average_score,
            turns=scenario['turn_count']
        )

        return conclusion

    def _get_grade(self, score: float) -> str:
        """Convert numerical score to letter grade"""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

    def get_scenario(self, scenario_id: str) -> Optional[Dict]:
        """Retrieve active scenario"""
        return self.active_scenarios.get(scenario_id)

    def cleanup_scenario(self, scenario_id: str):
        """Remove scenario from active cache"""
        if scenario_id in self.active_scenarios:
            del self.active_scenarios[scenario_id]
            logger.debug("scenario_cleaned_up", scenario_id=scenario_id)

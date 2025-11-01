import asyncio
import httpx
import structlog
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = structlog.get_logger()

@dataclass
class OpenRouterConfig:
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    primary_model: str = "anthropic/claude-3.5-sonnet"
    fallback_model: str = "anthropic/claude-3-haiku"
    timeout: int = 30
    max_retries: int = 3

class OpenRouterClient:
    """Client for interacting with OpenRouter API"""

    def __init__(self, config: OpenRouterConfig):
        self.config = config
        # Log API key configuration status (masked for security)
        api_key_masked = f"{config.api_key[:8]}...{config.api_key[-4:]}" if len(config.api_key) > 12 else "***"
        logger.info(
            "openrouter_config_loaded",
            api_key_prefix=api_key_masked,
            base_url=config.base_url,
            primary_model=config.primary_model,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
        
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "HTTP-Referer": "https://cogniplay.bot",
                "X-Title": "CogniPlay"
            }
        )
        self._token_usage = {"total_tokens": 0, "cost": 0.0}

    async def generate_character_response(
        self,
        character: Dict[str, Any],
        user_action: str,
        context: Dict[str, Any],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate AI character response to user action

        Args:
            character: Character profile and traits
            user_action: User's decision or statement
            context: Scenario context and history
            model: Override default model

        Returns:
            Dict with response, narrative_branch, and metadata
        """
        model = model or self.config.primary_model

        prompt = self._build_character_prompt(character, user_action, context)

        try:
            response = await self._make_request(
                model=model,
                messages=prompt,
                temperature=0.7,
                max_tokens=500
            )

            parsed = self._parse_character_response(response)

            logger.info(
                "character_response_generated",
                character_name=character.get('name'),
                tokens=response.get('usage', {}).get('total_tokens'),
                model=model
            )

            return parsed

        except Exception as e:
            logger.error(
                "character_generation_failed",
                error=str(e),
                character=character.get('name'),
                model=model
            )

            # Fallback to simpler model
            if model == self.config.primary_model:
                logger.info("falling_back_to_backup_model")
                return await self.generate_character_response(
                    character, user_action, context,
                    model=self.config.fallback_model
                )
            raise

    async def generate_scenario(
        self,
        scenario_type: str,
        difficulty: int,
        preferences: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate new role-playing scenario"""

        prompt = self._build_scenario_prompt(
            scenario_type, difficulty, preferences
        )

        response = await self._make_request(
            model=self.config.primary_model,
            messages=prompt,
            temperature=0.8,
            max_tokens=800
        )

        return self._parse_scenario_response(response)

    async def _make_request(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Dict[str, Any]:
        """Make request to OpenRouter API with retry logic"""

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post(
                    "/chat/completions",
                    json=payload
                )
                response.raise_for_status()

                data = response.json()
                self._track_usage(data)

                return data

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt
                    logger.warning(
                        "rate_limited",
                        attempt=attempt,
                        wait_seconds=wait_time
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise
            except httpx.TimeoutException:
                logger.warning("request_timeout", attempt=attempt)
                if attempt == self.config.max_retries - 1:
                    raise
                continue

        raise Exception("Max retries exceeded")

    def _build_character_prompt(
        self,
        character: Dict,
        user_action: str,
        context: Dict
    ) -> list:
        """Build prompt for character response generation"""

        personality = character.get('personality_traits', {})
        history = context.get('interaction_history', [])

        system_prompt = f"""You are roleplaying as {character['name']}, a {character['role']}.

Personality Traits:
- Temperament: {personality.get('temperament', 'Neutral')}
- Communication Style: {personality.get('communication_style', 'Professional')}
- Emotional State: {personality.get('emotional_state', 'Calm')}
- Goals: {personality.get('goals', 'Unknown')}

Background: {character.get('background', 'No specific background provided')}

Scenario Context: {context.get('situation', '')}

Instructions:
1. Stay in character throughout the interaction
2. Respond naturally to the user's action
3. Be consistent with your personality traits
4. Drive the narrative forward with your response
5. Provide 2-3 realistic action options for the user at the end
6. Keep responses concise (2-3 paragraphs max)

Format your response as:
RESPONSE: [Your character's dialogue and actions]
NARRATIVE: [Brief description of outcome/impact]
OPTIONS: [option1] | [option2] | [option3]"""

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for interaction in history[-3:]:  # Last 3 interactions
            messages.append({
                "role": "user",
                "content": f"User action: {interaction['user_action']}"
            })
            messages.append({
                "role": "assistant",
                "content": interaction['ai_response']
            })

        # Current user action
        messages.append({
            "role": "user",
            "content": f"User action: {user_action}"
        })

        return messages

    def _build_scenario_prompt(
        self,
        scenario_type: str,
        difficulty: int,
        preferences: Optional[Dict]
    ) -> list:
        """Build prompt for scenario generation"""

        difficulty_desc = {
            1: "Simple, straightforward situation with clear solutions",
            2: "Moderate complexity with some competing interests",
            3: "Complex situation with multiple stakeholders",
            4: "Challenging scenario with hidden information",
            5: "Highly complex with time pressure and conflicting goals"
        }

        system_prompt = f"""Generate a role-playing scenario for cognitive training.

Scenario Type: {scenario_type}
Difficulty Level: {difficulty}/5 - {difficulty_desc.get(difficulty, '')}

Requirements:
1. Create 1-2 distinct AI characters with clear personalities
2. Set up a realistic situation requiring decision-making
3. Include clear context and background
4. Provide initial decision points
5. Make it engaging and educational

Format your response as JSON:
{{
  "title": "Scenario title",
  "context": "Background situation",
  "characters": [
    {{
      "name": "Character name",
      "role": "Their role",
      "personality_traits": {{
        "temperament": "...",
        "communication_style": "...",
        "emotional_state": "...",
        "goals": "..."
      }},
      "background": "Brief background"
    }}
  ],
  "initial_situation": "Opening scenario description",
  "initial_options": ["option1", "option2", "option3"]
}}"""

        return [{"role": "system", "content": system_prompt}]

    def _parse_character_response(self, response: Dict) -> Dict[str, Any]:
        """Parse AI response into structured format"""

        content = response['choices'][0]['message']['content']

        # Parse structured response
        parsed = {
            'response': '',
            'narrative': '',
            'options': [],
            'raw_content': content
        }

        lines = content.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if line.startswith('RESPONSE:'):
                current_section = 'response'
                parsed['response'] = line[9:].strip()
            elif line.startswith('NARRATIVE:'):
                current_section = 'narrative'
                parsed['narrative'] = line[10:].strip()
            elif line.startswith('OPTIONS:'):
                options_text = line[8:].strip()
                parsed['options'] = [
                    opt.strip() for opt in options_text.split('|')
                ]
            elif current_section and line:
                parsed[current_section] += ' ' + line

        return parsed

    def _parse_scenario_response(self, response: Dict) -> Dict[str, Any]:
        """Parse scenario generation response"""

        content = response['choices'][0]['message']['content']

        # Try to parse as JSON
        try:
            import json
            import re

            # Remove markdown code blocks if present
            content = content.strip()

            # Remove any text before the first { or [
            json_start = content.find('{')
            if json_start == -1:
                json_start = content.find('[')
            if json_start > 0:
                content = content[json_start:]

            # Remove any text after the last } or ]
            json_end = content.rfind('}')
            if json_end == -1:
                json_end = content.rfind(']')
            if json_end >= 0:
                content = content[:json_end + 1]

            # Remove any remaining markdown formatting
            content = re.sub(r'```\w*\n?', '', content)

            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("scenario_parse_failed", content=content, error=str(e))
            raise

    def _track_usage(self, response: Dict):
        """Track token usage and costs"""
        usage = response.get('usage', {})
        tokens = usage.get('total_tokens', 0)

        self._token_usage['total_tokens'] += tokens

        # Rough cost estimation (adjust based on actual pricing)
        # Claude 3.5 Sonnet: ~$3 per 1M input tokens, ~$15 per 1M output
        cost = (tokens / 1_000_000) * 5  # Average estimate
        self._token_usage['cost'] += cost

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current session usage statistics"""
        return self._token_usage.copy()

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

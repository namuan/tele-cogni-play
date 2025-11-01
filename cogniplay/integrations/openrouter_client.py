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

    async def generate_logic_exercise(
        self,
        exercise_type: str,
        difficulty: int
    ) -> Dict[str, Any]:
        """Generate logic exercise using LLM"""

        prompt = self._build_logic_exercise_prompt(
            exercise_type, difficulty
        )

        response = await self._make_request(
            model=self.config.primary_model,
            messages=prompt,
            temperature=0.8,
            max_tokens=400
        )

        return self._parse_logic_exercise_response(response)

    async def generate_problem_solving_exercise(
        self,
        problem_type: str,
        difficulty: int
    ) -> Dict[str, Any]:
        """Generate problem-solving exercise using LLM"""

        # Validate problem type
        valid_problem_types = ['optimization', 'resource_allocation', 'strategy', 'multi-step']
        if problem_type not in valid_problem_types:
            raise ValueError(f"Invalid problem type: {problem_type}. Must be one of: {valid_problem_types}")

        # Validate difficulty
        if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 5:
            raise ValueError(f"Difficulty must be an integer between 1 and 5, got: {difficulty}")

        prompt = self._build_problem_solving_prompt(
            problem_type, difficulty
        )

        try:
            response = await self._make_request(
                model=self.config.primary_model,
                messages=prompt,
                temperature=0.8,
                max_tokens=500
            )

            parsed_response = self._parse_problem_solving_response(response)

            logger.info(
                "problem_solving_exercise_generated",
                problem_type=problem_type,
                difficulty=difficulty,
                tokens=response.get('usage', {}).get('total_tokens'),
                model=self.config.primary_model
            )

            return parsed_response

        except Exception as e:
            logger.error(
                "problem_solving_generation_failed",
                error=str(e),
                problem_type=problem_type,
                difficulty=difficulty,
                model=self.config.primary_model
            )

            # Fallback to simpler model
            if self.config.primary_model != self.config.fallback_model:
                logger.info("falling_back_to_backup_model_for_problem_solving")
                try:
                    response = await self._make_request(
                        model=self.config.fallback_model,
                        messages=prompt,
                        temperature=0.8,
                        max_tokens=500
                    )
                    return self._parse_problem_solving_response(response)
                except Exception as fallback_error:
                    logger.error(
                        "fallback_model_also_failed",
                        error=str(fallback_error),
                        problem_type=problem_type,
                        difficulty=difficulty
                    )
            
            raise

    async def generate_pattern_recognition_exercise(
        self,
        exercise_type: str,
        difficulty: int
    ) -> Dict[str, Any]:
        """Generate pattern recognition exercise using LLM"""

        # Validate exercise type
        valid_exercise_types = ['number_sequence', 'analogy', 'classification', 'visual_pattern', 'sequence_completion']
        if exercise_type not in valid_exercise_types:
            raise ValueError(f"Invalid exercise type: {exercise_type}. Must be one of: {valid_exercise_types}")

        # Validate difficulty
        if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 5:
            raise ValueError(f"Difficulty must be an integer between 1 and 5, got: {difficulty}")

        prompt = self._build_pattern_recognition_prompt(
            exercise_type, difficulty
        )

        try:
            response = await self._make_request(
                model=self.config.primary_model,
                messages=prompt,
                temperature=0.8,
                max_tokens=500
            )

            parsed_response = self._parse_pattern_recognition_response(response)

            logger.info(
                "pattern_recognition_exercise_generated",
                exercise_type=exercise_type,
                difficulty=difficulty,
                tokens=response.get('usage', {}).get('total_tokens'),
                model=self.config.primary_model
            )

            return parsed_response

        except Exception as e:
            logger.error(
                "pattern_recognition_generation_failed",
                error=str(e),
                exercise_type=exercise_type,
                difficulty=difficulty,
                model=self.config.primary_model
            )

            # Fallback to simpler model
            if self.config.primary_model != self.config.fallback_model:
                logger.info("falling_back_to_backup_model_for_pattern_recognition")
                try:
                    response = await self._make_request(
                        model=self.config.fallback_model,
                        messages=prompt,
                        temperature=0.8,
                        max_tokens=500
                    )
                    return self._parse_pattern_recognition_response(response)
                except Exception as fallback_error:
                    logger.error(
                        "fallback_model_also_failed",
                        error=str(fallback_error),
                        exercise_type=exercise_type,
                        difficulty=difficulty
                    )
            
            raise

    async def generate_memory_exercise(
        self,
        exercise_type: str,
        difficulty: int
    ) -> Dict[str, Any]:
        """Generate memory exercise using LLM"""

        # Validate exercise type
        valid_exercise_types = ['sequence_recall', 'word_list', 'number_memory', 'pattern_memory']
        if exercise_type not in valid_exercise_types:
            raise ValueError(f"Invalid exercise type: {exercise_type}. Must be one of: {valid_exercise_types}")

        # Validate difficulty
        if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 5:
            raise ValueError(f"Difficulty must be an integer between 1 and 5, got: {difficulty}")

        prompt = self._build_memory_exercise_prompt(
            exercise_type, difficulty
        )

        try:
            response = await self._make_request(
                model=self.config.primary_model,
                messages=prompt,
                temperature=0.8,
                max_tokens=500
            )

            parsed_response = self._parse_memory_exercise_response(response)

            logger.info(
                "memory_exercise_generated",
                exercise_type=exercise_type,
                difficulty=difficulty,
                tokens=response.get('usage', {}).get('total_tokens'),
                model=self.config.primary_model
            )

            return parsed_response

        except Exception as e:
            logger.error(
                "memory_exercise_generation_failed",
                error=str(e),
                exercise_type=exercise_type,
                difficulty=difficulty,
                model=self.config.primary_model
            )

            # Fallback to simpler model
            if self.config.primary_model != self.config.fallback_model:
                logger.info("falling_back_to_backup_model_for_memory")
                try:
                    response = await self._make_request(
                        model=self.config.fallback_model,
                        messages=prompt,
                        temperature=0.8,
                        max_tokens=500
                    )
                    return self._parse_memory_exercise_response(response)
                except Exception as fallback_error:
                    logger.error(
                        "fallback_model_also_failed_for_memory",
                        error=str(fallback_error),
                        exercise_type=exercise_type,
                        difficulty=difficulty
                    )
            
            raise

    async def generate_attention_exercise(
        self,
        exercise_type: str,
        difficulty: int
    ) -> Dict[str, Any]:
        """Generate attention exercise using LLM"""

        # Validate exercise type
        valid_exercise_types = ['selective_attention', 'information_filtering', 'focus_challenge']
        if exercise_type not in valid_exercise_types:
            raise ValueError(f"Invalid exercise type: {exercise_type}. Must be one of: {valid_exercise_types}")

        # Validate difficulty
        if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 5:
            raise ValueError(f"Difficulty must be an integer between 1 and 5, got: {difficulty}")

        prompt = self._build_attention_exercise_prompt(
            exercise_type, difficulty
        )

        try:
            response = await self._make_request(
                model=self.config.primary_model,
                messages=prompt,
                temperature=0.8,
                max_tokens=500
            )

            parsed_response = self._parse_attention_exercise_response(response)

            logger.info(
                "attention_exercise_generated",
                exercise_type=exercise_type,
                difficulty=difficulty,
                tokens=response.get('usage', {}).get('total_tokens'),
                model=self.config.primary_model
            )

            return parsed_response

        except Exception as e:
            logger.error(
                "attention_generation_failed",
                error=str(e),
                exercise_type=exercise_type,
                difficulty=difficulty,
                model=self.config.primary_model
            )

            # Fallback to simpler model
            if self.config.primary_model != self.config.fallback_model:
                logger.info("falling_back_to_backup_model_for_attention")
                try:
                    response = await self._make_request(
                        model=self.config.fallback_model,
                        messages=prompt,
                        temperature=0.8,
                        max_tokens=500
                    )
                    return self._parse_attention_exercise_response(response)
                except Exception as fallback_error:
                    logger.error(
                        "fallback_model_also_failed",
                        error=str(fallback_error),
                        exercise_type=exercise_type,
                        difficulty=difficulty
                    )
            
            raise

    def _build_attention_exercise_prompt(
        self,
        exercise_type: str,
        difficulty: int
    ) -> list:
        """Build prompt for attention exercise generation"""

        difficulty_descriptions = {
            1: "Simple attention exercises with clear focus requirements and minimal distractions",
            2: "Moderate complexity with some competing information and basic filtering needs",
            3: "Complex attention tasks requiring sustained focus and information prioritization",
            4: "Challenging exercises with multiple distractions and complex filtering requirements",
            5: "Highly complex attention tasks with heavy cognitive load and sophisticated filtering"
        }

        type_specific_instructions = {
            'selective_attention': """Create a selective attention exercise where users must focus on specific information while ignoring distractions.
                                    Include a main task with competing information that requires careful attention to detail.""",
            'information_filtering': """Create an information filtering exercise where users must identify and extract relevant information from a larger set.
                                      Include both relevant and irrelevant information that needs to be distinguished.""",
            'focus_challenge': """Create a focus challenge exercise that requires sustained attention and resistance to distractions.
                                 Include tasks that test the ability to maintain focus over time and through interruptions."""
        }

        system_prompt = f"""Generate a {exercise_type} attention exercise for cognitive training.

Exercise Type: {exercise_type}
Difficulty Level: {difficulty}/5 - {difficulty_descriptions.get(difficulty, '')}

Specific Instructions:
{type_specific_instructions.get(exercise_type, 'Create an engaging attention exercise.')}

Requirements:
1. Create a clear attention task that tests focus and concentration
2. Include specific instructions that guide the user on what to pay attention to
3. Provide a definitive correct answer based on the attention requirements
4. Include 2-3 helpful hints that guide attention without giving away the answer
5. Set appropriate time limits based on difficulty
6. For multiple choice questions, provide realistic but incorrect distractors
7. Ensure the exercise genuinely tests attention and focus skills

Format your response as JSON:
{{
  "question": "The attention exercise with full context and instructions",
  "answer": "The correct answer based on attention requirements",
  "options": ["option1", "option2", "option3"], // for multiple choice only
  "hints": ["hint1", "hint2", "hint3"],
  "attention_focus": "Brief explanation of what aspect of attention is being tested"
}}"""

        return [{"role": "system", "content": system_prompt}]

    def _build_memory_exercise_prompt(
        self,
        exercise_type: str,
        difficulty: int
    ) -> list:
        """Build prompt for memory exercise generation"""

        difficulty_descriptions = {
            1: "Simple memory tasks with short sequences and minimal items to remember",
            2: "Moderate complexity with slightly longer sequences and more items",
            3: "Complex memory tasks requiring sustained attention and multiple items",
            4: "Challenging exercises with longer sequences and complex patterns",
            5: "Highly complex memory tasks with maximum cognitive load and extensive sequences"
        }

        type_specific_instructions = {
            'sequence_recall': """Create a sequence recall exercise where users must remember and reproduce a sequence of symbols, colors, or items.
                                  Include clear display time and format instructions.""",
            'word_list': """Create a word list memory exercise where users study a list of words and must recall them later.
                           Include study time recommendations and format instructions for recall.""",
            'number_memory': """Create a number sequence memory exercise where users must remember and reproduce number sequences.
                               Include appropriate length based on difficulty and clear recall instructions.""",
            'pattern_memory': """Create a visual pattern memory exercise where users study a grid pattern and must recreate it.
                                Include clear grid dimensions and reproduction instructions."""
        }

        system_prompt = f"""Generate a {exercise_type} memory exercise for cognitive training.

Exercise Type: {exercise_type}
Difficulty Level: {difficulty}/5 - {difficulty_descriptions.get(difficulty, '')}

Specific Instructions:
{type_specific_instructions.get(exercise_type, 'Create an engaging memory exercise.')}

Requirements:
1. Create a clear memory task that challenges working memory capacity
2. Include specific instructions for study time and recall format
3. Provide a definitive correct answer based on the memory requirement
4. Include 2-3 helpful hints that guide memory without giving away the answer
5. Set appropriate time limits based on difficulty and memory load
6. For multiple choice questions, provide realistic but incorrect distractors
7. Ensure the exercise genuinely tests memory and recall abilities
8. Scale the memory load (sequence length, number of items, etc.) with difficulty

Format your response as JSON:
{{
  "question": "The memory exercise with full context, study instructions, and recall format",
  "answer": "The correct answer that should be recalled",
  "options": ["option1", "option2", "option3"], // for multiple choice only
  "hints": ["hint1", "hint2", "hint3"],
  "study_time_seconds": X, // suggested study time in seconds
  "memory_load": "Brief description of what needs to be remembered"
}}"""

        return [{"role": "system", "content": system_prompt}]

    def _parse_memory_exercise_response(self, response: Dict) -> Dict[str, Any]:
        """Parse memory exercise generation response"""

        content = response['choices'][0]['message']['content']

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

            # Clean up common LLM JSON issues
            # Remove JavaScript-style comments
            content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
            # Remove trailing commas before closing brackets/braces
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            # Fix common escaping issues
            content = content.replace('\\n', ' ').replace('\\"', '"')
            # Remove extra whitespace that might cause issues
            content = re.sub(r'\s+', ' ', content).strip()

            parsed_data = json.loads(content)

            # Ensure all required fields are present with defaults
            return {
                'question': parsed_data.get('question', ''),
                'answer': parsed_data.get('answer', ''),
                'options': parsed_data.get('options'),
                'hints': parsed_data.get('hints', []),
                'study_time_seconds': parsed_data.get('study_time_seconds'),
                'memory_load': parsed_data.get('memory_load', '')
            }

        except json.JSONDecodeError as e:
            logger.error("memory_exercise_parse_failed", content=content, error=str(e))
            raise
        except Exception as e:
            logger.error("memory_exercise_parse_error", content=content, error=str(e))
            raise

    def _parse_attention_exercise_response(self, response: Dict) -> Dict[str, Any]:
        """Parse attention exercise generation response"""

        content = response['choices'][0]['message']['content']

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

            # Clean up common LLM JSON issues
            # Remove JavaScript-style comments
            content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
            # Remove trailing commas before closing brackets/braces
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            # Fix common escaping issues
            content = content.replace('\\n', ' ').replace('\\"', '"')
            # Remove extra whitespace that might cause issues
            content = re.sub(r'\s+', ' ', content).strip()

            parsed_data = json.loads(content)

            # Ensure all required fields are present with defaults
            return {
                'question': parsed_data.get('question', ''),
                'answer': parsed_data.get('answer', ''),
                'options': parsed_data.get('options'),
                'hints': parsed_data.get('hints', []),
                'attention_focus': parsed_data.get('attention_focus', '')
            }

        except json.JSONDecodeError as e:
            logger.error("attention_exercise_parse_failed", content=content, error=str(e))
            raise
        except Exception as e:
            logger.error("attention_exercise_parse_error", content=content, error=str(e))
            raise

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

        # Log the request payload for debugging
        logger.info(
            "openrouter_request",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            message_count=len(messages),
            request_body=payload
        )

        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post(
                    "/chat/completions",
                    json=payload
                )
                response.raise_for_status()

                data = response.json()
                
                # Log the full response for debugging
                logger.info(
                    "openrouter_response",
                    status_code=response.status_code,
                    response_body=data,
                    attempt=attempt + 1
                )
                
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

    def _build_logic_exercise_prompt(
        self,
        exercise_type: str,
        difficulty: int
    ) -> list:
        """Build prompt for logic exercise generation"""

        difficulty_descriptions = {
            1: "Simple, straightforward logic with basic reasoning",
            2: "Moderate complexity with some intermediate steps",
            3: "Moderately complex logic requiring multiple steps",
            4: "Challenging logic with multiple conditions and branches",
            5: "Highly complex logic with advanced reasoning patterns"
        }

        type_specific_instructions = {
            'syllogism': """Create a syllogism puzzle with 2-3 premises and a conclusion question.
                          Example: 'All A are B. All B are C. Therefore... ?' """,
            'deduction': """Create a deductive reasoning puzzle with clear clues and constraints.
                          Include enough information to reach a definite answer.""",
            'riddle': """Create an engaging riddle with clear clues that lead to a single answer.
                       Make it challenging but solvable.""",
            'grid_logic': """Create a grid-based logic puzzle with 2-3 categories and clear clues.
                           Ensure it's solvable with the given information."""
        }

        system_prompt = f"""Generate a {exercise_type} logic exercise for cognitive training.

Exercise Type: {exercise_type}
Difficulty Level: {difficulty}/5 - {difficulty_descriptions.get(difficulty, '')}

Specific Instructions:
{type_specific_instructions.get(exercise_type, 'Create an engaging logic puzzle.')}

Requirements:
1. Create a clear, challenging but solvable puzzle
2. Provide a definitive correct answer
3. Include 2-3 helpful hints if applicable
4. Set appropriate time limits based on difficulty
5. For multiple choice questions, provide realistic but incorrect distractors

Format your response as JSON:
{{
  "question": "The puzzle question with full context",
  "answer": "The correct answer",
  "options": ["option1", "option2", "option3"], // for multiple choice only
  "hints": ["hint1", "hint2", "hint3"]
}}"""

        return [{"role": "system", "content": system_prompt}]

    def _build_problem_solving_prompt(
        self,
        problem_type: str,
        difficulty: int
    ) -> list:
        """Build prompt for problem-solving exercise generation"""

        difficulty_descriptions = {
            1: "Simple, straightforward problem with clear constraints and obvious solutions",
            2: "Moderate complexity with some competing factors and multiple approaches",
            3: "Complex problem requiring analysis of multiple variables and trade-offs",
            4: "Challenging scenario with limited information and conflicting priorities",
            5: "Highly complex problem with time pressure, resource constraints, and multiple stakeholders"
        }

        type_specific_instructions = {
            'optimization': """Create a business optimization problem focused on maximizing efficiency, minimizing costs, or optimizing resource usage.
                            Include constraints, variables to optimize, and clear metrics for success.""",
            'resource_allocation': """Create a resource allocation problem involving people, budget, time, or materials.
                                    Include limited resources, competing demands, and allocation constraints.""",
            'strategy': """Create a strategic decision-making problem requiring analysis of options, risks, and outcomes.
                         Include multiple approaches with different pros and cons, and clear success criteria.""",
            'multi-step': """Create a multi-step problem requiring sequential decision-making and dependency analysis.
                           Include initial conditions, multiple decision points, and cascading consequences."""
        }

        system_prompt = f"""Generate a {problem_type} problem-solving exercise for cognitive training.

Problem Type: {problem_type}
Difficulty Level: {difficulty}/5 - {difficulty_descriptions.get(difficulty, '')}

Specific Instructions:
{type_specific_instructions.get(problem_type, 'Create an engaging business problem-solving scenario.')}

Requirements:
1. Create a realistic business/management scenario
2. Include clear problem statement and context
3. Provide 3-4 realistic solution options where appropriate
4. Include a definitive correct answer or best approach
5. Add 2-3 helpful hints that guide without giving away the answer
6. Make it challenging but solvable based on the difficulty level
7. Focus on practical business/management applications

Format your response as JSON:
{{
  "scenario": "Detailed problem scenario with context",
  "question": "The specific question to solve",
  "options": ["option1", "option2", "option3", "option4"], // for multiple choice only
  "correct_answer": "The correct answer or best approach",
  "hints": ["hint1", "hint2", "hint3"],
  "explanation": "Brief explanation of why this is the correct approach"
}}"""

        return [{"role": "system", "content": system_prompt}]

    def _build_pattern_recognition_prompt(
        self,
        exercise_type: str,
        difficulty: int
    ) -> list:
        """Build prompt for pattern recognition exercise generation"""

        difficulty_descriptions = {
            1: "Simple, straightforward patterns with clear rules and obvious next elements",
            2: "Moderate complexity with some intermediate steps and multiple pattern types",
            3: "Moderately complex patterns requiring analysis of multiple relationships",
            4: "Challenging patterns with multiple layers and abstract relationships",
            5: "Highly complex patterns with advanced mathematical or logical reasoning"
        }

        type_specific_instructions = {
            'number_sequence': """Create a number sequence puzzle with a clear mathematical pattern.
                               Include 4-5 numbers with one missing element at the end.
                               Ensure the pattern is solvable and has a logical progression.""",
            'analogy': """Create an analogy puzzle showing relationships between concepts.
                        Format: 'A is to B as C is to ___' or similar patterns.
                        Use clear, relatable concepts with logical relationships.""",
            'classification': """Create a classification puzzle where items need to be grouped or one item doesn't belong.
                               Provide 4-5 items with clear logical categories.
                               Make the classification rule clear but not obvious.""",
            'visual_pattern': """Create a visual pattern description using text symbols or shapes.
                               Describe a 2D pattern with clear progression rules.
                               Use simple geometric shapes or symbols that can be easily visualized.""",
            'sequence_completion': """Create a sequence completion puzzle with mixed elements.
                                    Combine numbers, letters, or symbols in a logical sequence.
                                    Include 3-4 elements with one missing to complete the pattern."""
        }

        system_prompt = f"""Generate a {exercise_type} pattern recognition exercise for cognitive training.

Exercise Type: {exercise_type}
Difficulty Level: {difficulty}/5 - {difficulty_descriptions.get(difficulty, '')}

Specific Instructions:
{type_specific_instructions.get(exercise_type, 'Create an engaging pattern recognition puzzle.')}

Requirements:
1. Create a clear, challenging but solvable pattern
2. Provide a definitive correct answer
3. Include 2-3 helpful hints that guide without giving away the answer
4. Set appropriate time limits based on difficulty
5. For multiple choice questions, provide realistic but incorrect distractors
6. Ensure the pattern follows logical rules and is educational

Format your response as JSON:
{{
  "question": "The pattern recognition question with full context",
  "answer": "The correct answer",
  "options": ["option1", "option2", "option3"], // for multiple choice only
  "hints": ["hint1", "hint2", "hint3"],
  "pattern_explanation": "Brief explanation of the pattern rule"
}}"""

        return [{"role": "system", "content": system_prompt}]

    def _parse_pattern_recognition_response(self, response: Dict) -> Dict[str, Any]:
        """Parse pattern recognition exercise generation response"""

        content = response['choices'][0]['message']['content']

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

            # Clean up common LLM JSON issues
            # Remove JavaScript-style comments
            content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
            # Remove trailing commas before closing brackets/braces
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            # Fix common escaping issues
            content = content.replace('\\n', ' ').replace('\\"', '"')
            # Remove extra whitespace that might cause issues
            content = re.sub(r'\s+', ' ', content).strip()

            parsed_data = json.loads(content)

            # Ensure all required fields are present with defaults
            return {
                'question': parsed_data.get('question', ''),
                'answer': parsed_data.get('answer', ''),
                'options': parsed_data.get('options'),
                'hints': parsed_data.get('hints', []),
                'pattern_explanation': parsed_data.get('pattern_explanation', '')
            }

        except json.JSONDecodeError as e:
            logger.error("pattern_recognition_parse_failed", content=content, error=str(e))
            raise
        except Exception as e:
            logger.error("pattern_recognition_parse_error", content=content, error=str(e))
            raise

    def _parse_problem_solving_response(self, response: Dict) -> Dict[str, Any]:
        """Parse problem-solving exercise generation response"""

        content = response['choices'][0]['message']['content']

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

            # Clean up common LLM JSON issues
            # Remove JavaScript-style comments
            content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
            # Remove trailing commas before closing brackets/braces
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            # Fix common escaping issues
            content = content.replace('\\n', ' ').replace('\\"', '"')
            # Remove extra whitespace that might cause issues
            content = re.sub(r'\s+', ' ', content).strip()

            parsed_data = json.loads(content)

            # Ensure all required fields are present with defaults
            return {
                'scenario': parsed_data.get('scenario', ''),
                'question': parsed_data.get('question', ''),
                'options': parsed_data.get('options'),
                'correct_answer': parsed_data.get('correct_answer', ''),
                'hints': parsed_data.get('hints', []),
                'explanation': parsed_data.get('explanation', '')
            }

        except json.JSONDecodeError as e:
            logger.error("problem_solving_parse_failed", content=content, error=str(e))
            raise
        except Exception as e:
            logger.error("problem_solving_parse_error", content=content, error=str(e))
            raise

    def _parse_logic_exercise_response(self, response: Dict) -> Dict[str, Any]:
        """Parse logic exercise generation response"""

        content = response['choices'][0]['message']['content']

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

            # Clean up common LLM JSON issues
            # Remove JavaScript-style comments
            content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
            # Remove trailing commas before closing brackets/braces
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            # Fix common escaping issues
            content = content.replace('\\n', ' ').replace('\\"', '"')
            # Remove extra whitespace that might cause issues
            content = re.sub(r'\s+', ' ', content).strip()

            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error("logic_exercise_parse_failed", content=content, error=str(e))
            raise

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

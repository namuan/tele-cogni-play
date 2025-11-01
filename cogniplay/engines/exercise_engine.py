import uuid
import random
import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime
from cogniplay.data.models import Exercise, ExerciseResult
from cogniplay.integrations.openrouter_client import OpenRouterClient

logger = structlog.get_logger()

class ExerciseEngine:
    """Generate and validate cognitive exercises"""

    def __init__(self, openrouter_client=None):
        self.client = openrouter_client
        self.generators = {
            'memory': MemoryExerciseGenerator(),
            'logic': LogicExerciseGenerator(openrouter_client),
            'problem_solving': ProblemSolvingGenerator(openrouter_client),
            'pattern_recognition': PatternRecognitionGenerator(openrouter_client),
            'attention': AttentionExerciseGenerator(openrouter_client)
        }

    async def generate_exercise(
        self,
        category: str,
        difficulty: int
    ) -> Exercise:
        """
        Generate new exercise based on category and difficulty

        Args:
            category: Exercise category (memory, logic, etc.)
            difficulty: Difficulty level (1-5)

        Returns:
            Exercise object
        """

        if category not in self.generators:
            raise ValueError(f"Unknown category: {category}")

        generator = self.generators[category]
        exercise = await generator.generate(difficulty)

        logger.info(
            "exercise_generated",
            exercise_id=exercise.id,
            category=category,
            type=exercise.type,
            difficulty=difficulty
        )

        return exercise

    async def validate_answer(
        self,
        exercise: Exercise,
        user_answer: Any,
        completion_time: int,
        hints_used: int = 0
    ) -> ExerciseResult:
        """
        Validate user's answer and calculate score

        Args:
            exercise: Exercise object
            user_answer: User's submitted answer
            completion_time: Time taken in seconds
            hints_used: Number of hints used

        Returns:
            ExerciseResult with scoring details
        """

        generator = self.generators[exercise.category]
        is_correct = await generator.validate(
            exercise.correct_answer,
            user_answer
        )

        # Calculate score (0-100)
        base_score = 100 if is_correct else 0

        # Time bonus/penalty
        if exercise.time_limit_seconds and is_correct:
            time_ratio = completion_time / exercise.time_limit_seconds
            if time_ratio < 0.5:
                base_score += 10  # Fast completion bonus
            elif time_ratio > 1.0:
                base_score -= 10  # Penalty for exceeding time

        # Hint penalty
        base_score -= (hints_used * 5)

        # Ensure score is within bounds
        score = max(0, min(100, base_score))

        # Accuracy (simplified for now)
        accuracy = 100.0 if is_correct else 0.0

        result = ExerciseResult(
            exercise_id=exercise.id,
            user_answer=user_answer,
            is_correct=is_correct,
            score=score,
            accuracy=accuracy,
            completion_time=completion_time,
            hints_used=hints_used
        )

        logger.info(
            "exercise_validated",
            exercise_id=exercise.id,
            is_correct=is_correct,
            score=score,
            completion_time=completion_time
        )

        return result

    def get_categories(self) -> List[str]:
        """Get list of available exercise categories"""
        return list(self.generators.keys())


class MemoryExerciseGenerator:
    """Generate memory exercises"""

    async def generate(self, difficulty: int) -> Exercise:
        """Generate memory exercise based on difficulty"""

        exercise_types = [
            self._sequence_recall,
            self._word_list,
            self._number_memory,
            self._pattern_memory
        ]

        # Select random exercise type
        generator_func = random.choice(exercise_types)
        return generator_func(difficulty)

    def _sequence_recall(self, difficulty: int) -> Exercise:
        """Generate sequence recall exercise"""

        # Sequence length based on difficulty
        length_map = {1: 3, 2: 4, 3: 6, 4: 8, 5: 10}
        length = length_map.get(difficulty, 5)

        # Generate random sequence
        items = ['🔴', '🔵', '🟢', '🟡', '🟣', '🟠', '⚫', '⚪']
        sequence = [random.choice(items) for _ in range(length)]

        question = f"""Memory Challenge - Sequence Recall

Study this sequence for {5 + difficulty} seconds:

{' '.join(sequence)}

After the time is up, type the sequence back exactly as shown (include spaces between items)."""

        return Exercise(
            id=str(uuid.uuid4()),
            category='memory',
            type='sequence_recall',
            difficulty=difficulty,
            question=question,
            correct_answer=' '.join(sequence),
            options=None,
            time_limit_seconds=60,
            hints=[
                f"The sequence has {length} items",
                f"It starts with {sequence[0]}",
                f"It ends with {sequence[-1]}"
            ]
        )

    def _word_list(self, difficulty: int) -> Exercise:
        """Generate word list memory exercise"""

        count_map = {1: 5, 2: 7, 3: 10, 4: 15, 5: 20}
        count = count_map.get(difficulty, 10)

        word_pool = [
            'apple', 'mountain', 'computer', 'elephant', 'guitar',
            'ocean', 'bicycle', 'telephone', 'butterfly', 'camera',
            'pizza', 'rocket', 'library', 'diamond', 'forest',
            'lighthouse', 'saxophone', 'tornado', 'universe', 'waterfall',
            'microscope', 'adventure', 'sculpture', 'harmony', 'eclipse'
        ]

        words = random.sample(word_pool, count)

        question = f"""Memory Challenge - Word List

Study these {count} words for {10 + difficulty * 2} seconds:

{', '.join(words)}

After the time is up, type as many words as you can remember (separated by commas)."""

        return Exercise(
            id=str(uuid.uuid4()),
            category='memory',
            type='word_list',
            difficulty=difficulty,
            question=question,
            correct_answer=words,
            options=None,
            time_limit_seconds=120,
            hints=[
                f"There were {count} words total",
                f"One word started with '{words[0][0]}'",
                f"One word was '{words[random.randint(0, len(words)-1)]}'"
            ]
        )

    def _number_memory(self, difficulty: int) -> Exercise:
        """Generate number sequence memory"""

        length_map = {1: 4, 2: 6, 3: 8, 4: 10, 5: 12}
        length = length_map.get(difficulty, 6)

        number = ''.join([str(random.randint(0, 9)) for _ in range(length)])

        question = f"""Memory Challenge - Number Sequence

Remember this {length}-digit number:

{number}

Study it for {5 + difficulty} seconds, then type it back."""

        return Exercise(
            id=str(uuid.uuid4()),
            category='memory',
            type='number_memory',
            difficulty=difficulty,
            question=question,
            correct_answer=number,
            options=None,
            time_limit_seconds=45,
            hints=[
                f"The number has {length} digits",
                f"First digit is {number[0]}",
                f"Last digit is {number[-1]}"
            ]
        )

    def _pattern_memory(self, difficulty: int) -> Exercise:
        """Generate pattern memory exercise"""

        size_map = {1: 2, 2: 3, 3: 4, 4: 4, 5: 5}
        size = size_map.get(difficulty, 3)

        # Create grid pattern
        symbols = ['■', '□']
        pattern = []
        for i in range(size):
            row = [random.choice(symbols) for _ in range(size)]
            pattern.append(row)

        # Format pattern display
        pattern_str = '\n'.join([' '.join(row) for row in pattern])

        # Flatten for answer
        correct_answer = ''.join([''.join(row) for row in pattern])

        question = f"""Memory Challenge - Pattern Memory

Study this {size}x{size} pattern for {8 + difficulty * 2} seconds:

{pattern_str}

After time is up, recreate the pattern by typing the symbols row by row (no spaces).
Use ■ for filled squares and □ for empty squares."""

        return Exercise(
            id=str(uuid.uuid4()),
            category='memory',
            type='pattern_memory',
            difficulty=difficulty,
            question=question,
            correct_answer=correct_answer,
            options=None,
            time_limit_seconds=90,
            hints=[
                f"It's a {size}x{size} grid",
                f"Top-left corner is {pattern[0][0]}",
                f"Bottom-right corner is {pattern[-1][-1]}"
            ]
        )

    async def validate(self, correct_answer: Any, user_answer: Any) -> bool:
        """Validate memory exercise answer"""

        if isinstance(correct_answer, list):
            # Word list - check how many words match
            user_words = [w.strip().lower() for w in user_answer.split(',')]
            correct_words = [w.lower() for w in correct_answer]
            matches = sum(1 for w in user_words if w in correct_words)
            # Consider correct if at least 70% remembered
            return matches >= len(correct_words) * 0.7
        else:
            # Handle comma-separated answers with flexible spacing
            if ',' in str(correct_answer) and ',' in str(user_answer):
                correct_parts = [part.strip().lower() for part in str(correct_answer).split(',')]
                user_parts = [part.strip().lower() for part in str(user_answer).split(',')]
                # Check if all correct parts are present in user's answer (order doesn't matter)
                return set(correct_parts) == set(user_parts)
            else:
                # Exact match for simple answers
                return str(user_answer).strip().lower() == str(correct_answer).strip().lower()


class LogicExerciseGenerator:
    """Generate logic puzzles using LLM"""

    def __init__(self, openrouter_client=None):
        self.client = openrouter_client

    async def generate(self, difficulty: int) -> Exercise:
        """Generate logic exercise using LLM"""

        # If no LLM client, fall back to hardcoded generators
        if not self.client:
            exercise_types = [
                self._syllogism,
                self._deduction,
                self._riddle,
                self._grid_logic
            ]
            generator_func = random.choice(exercise_types)
            return generator_func(difficulty)

        # Use LLM to generate dynamic exercise
        return await self._generate_llm_exercise(difficulty)

    async def _generate_llm_exercise(self, difficulty: int) -> Exercise:
        """Generate logic exercise using LLM"""

        exercise_types = [
            "syllogism",
            "deduction",
            "riddle",
            "grid_logic"
        ]

        exercise_type = random.choice(exercise_types)

        try:
            # Generate exercise via LLM
            exercise_data = await self.client.generate_logic_exercise(
                exercise_type,
                difficulty
            )

            # Create Exercise object from LLM data
            return Exercise(
                id=str(uuid.uuid4()),
                category='logic',
                type=exercise_type,
                difficulty=difficulty,
                question=exercise_data['question'],
                correct_answer=exercise_data['answer'],
                options=exercise_data.get('options'),
                time_limit_seconds=60 + difficulty * 15,
                hints=exercise_data.get('hints', [
                    "Think carefully about the logic",
                    "Consider all possibilities",
                    "Check your reasoning"
                ])
            )

        except Exception as e:
            logger.warning(
                "llm_exercise_generation_failed",
                error=str(e),
                falling_back_to_hardcoded=True
            )
            # Fall back to hardcoded generator
            fallback_methods = {
                'syllogism': self._syllogism,
                'deduction': self._deduction,
                'riddle': self._riddle,
                'grid_logic': self._grid_logic
            }
            return fallback_methods[exercise_type](difficulty)

    def _syllogism(self, difficulty: int) -> Exercise:
        """Generate syllogism puzzle"""

        puzzles = {
            1: {
                'premises': [
                    "All cats are animals.",
                    "All animals need food.",
                    "Fluffy is a cat."
                ],
                'question': "Does Fluffy need food?",
                'answer': 'yes',
                'options': ['Yes', 'No', 'Cannot determine']
            },
            2: {
                'premises': [
                    "All managers attend meetings.",
                    "Sarah attends meetings.",
                    "John is not a manager."
                ],
                'question': "Does John attend meetings?",
                'answer': 'cannot determine',
                'options': ['Yes', 'No', 'Cannot determine']
            },
            3: {
                'premises': [
                    "No birds are mammals.",
                    "All bats are mammals.",
                    "Some flying creatures are birds."
                ],
                'question': "Are all flying creatures bats?",
                'answer': 'no',
                'options': ['Yes', 'No', 'Cannot determine']
            },
            4: {
                'premises': [
                    "All successful projects are well-planned.",
                    "Some well-planned projects have good teams.",
                    "Project X has a good team."
                ],
                'question': "Is Project X successful?",
                'answer': 'cannot determine',
                'options': ['Yes', 'No', 'Cannot determine']
            },
            5: {
                'premises': [
                    "No complete solutions are simple.",
                    "All elegant solutions are simple.",
                    "Some working solutions are complete."
                ],
                'question': "Can a working solution be elegant?",
                'answer': 'cannot determine',
                'options': ['Yes', 'No', 'Cannot determine']
            }
        }

        puzzle = puzzles.get(difficulty, puzzles[3])

        question = f"""Logic Puzzle - Syllogism

Given these statements:
{chr(10).join([f"{i+1}. {p}" for i, p in enumerate(puzzle['premises'])])}"""

        question += f"""

Question: {puzzle['question']}

Type your answer: {' / '.join(puzzle['options'])}"""

        return Exercise(
            id=str(uuid.uuid4()),
            category='logic',
            type='syllogism',
            difficulty=difficulty,
            question=question,
            correct_answer=puzzle['answer'],
            options=puzzle['options'],
            time_limit_seconds=60 + difficulty * 15,
            hints=[
                "Consider each premise carefully",
                "Draw a diagram if helpful",
                "Check if the conclusion necessarily follows"
            ]
        )

    def _deduction(self, difficulty: int) -> Exercise:
        """Generate deduction puzzle"""

        puzzles = {
            1: {
                'scenario': "Three friends - Alice, Bob, and Carol - each have a different pet: a dog, a cat, and a bird. Alice doesn't have a dog. Bob has a cat.",
                'question': "Who has the bird?",
                'answer': 'alice'
            },
            2: {
                'scenario': "Four people live on different floors of a building (1st to 4th floor). Dan lives above Emma but below Frank. Carol lives on the 1st floor.",
                'question': "Which floor does Frank live on?",
                'answer': '4'
            },
            3: {
                'scenario': "Five students scored differently on a test. Maya scored higher than Luke but lower than Nina. Oliver scored the lowest. Pam scored between Maya and Nina.",
                'question': "Who scored the highest?",
                'answer': 'nina'
            },
            4: {
                'scenario': "Six coworkers each prefer different lunch spots (A, B, C, D, E, F). Tom doesn't go to A or B. Rita goes to C. Sam goes to a spot alphabetically after Tom's. Quinn goes to E. Uma goes to the last spot alphabetically. Victor goes to the remaining spot.",
                'question': "Where does Tom go for lunch?",
                'answer': 'd'
            },
            5: {
                'scenario': "Seven runners finished a race. Alex finished before Beth but after Cara. Dana finished right after Cara. Emma finished last. Frank finished before Cara but after Gina.",
                'question': "Who finished first?",
                'answer': 'gina'
            }
        }

        puzzle = puzzles.get(difficulty, puzzles[3])

        question = f"""Logic Puzzle - Deduction

{puzzle['scenario']}

{puzzle['question']}

Type your answer:"""

        return Exercise(
            id=str(uuid.uuid4()),
            category='logic',
            type='deduction',
            difficulty=difficulty,
            question=question,
            correct_answer=puzzle['answer'],
            options=None,
            time_limit_seconds=90 + difficulty * 20,
            hints=[
                "Try writing down what you know",
                "Use process of elimination",
                "Work through the clues step by step"
            ]
        )

    def _riddle(self, difficulty: int) -> Exercise:
        """Generate riddle"""

        riddles = {
            1: {
                'riddle': "What has keys but no locks, space but no room, and you can enter but can't go inside?",
                'answer': 'keyboard'
            },
            2: {
                'riddle': "I speak without a mouth and hear without ears. I have no body, but come alive with wind. What am I?",
                'answer': 'echo'
            },
            3: {
                'riddle': "The more you take, the more you leave behind. What am I?",
                'answer': 'footsteps'
            },
            4: {
                'riddle': "I am taken from a mine and shut in a wooden case, from which I am never released, yet I am used by almost everyone. What am I?",
                'answer': 'pencil lead'
            },
            5: {
                'riddle': "At night they come without being fetched. By day they are lost without being stolen. What are they?",
                'answer': 'stars'
            }
        }

        puzzle = riddles.get(difficulty, riddles[3])

        question = f"""Logic Puzzle - Riddle

{puzzle['riddle']}

Type your answer:"""

        return Exercise(
            id=str(uuid.uuid4()),
            category='logic',
            type='riddle',
            difficulty=difficulty,
            question=question,
            correct_answer=puzzle['answer'],
            options=None,
            time_limit_seconds=120,
            hints=[
                "Think metaphorically",
                "Consider multiple meanings",
                "What fits all the clues?"
            ]
        )

    def _grid_logic(self, difficulty: int) -> Exercise:
        """Generate grid logic puzzle"""

        # Simplified for text format
        question = f"""Logic Puzzle - Grid Logic

Three people (Alex, Bailey, Casey) each have a favorite color (Red, Blue, Green) and a pet (Dog, Cat, Fish).

Clues:
1. Alex doesn't like Red
2. The person who likes Blue has a Cat
3. Casey has a Fish
4. Bailey doesn't like Green

Question: What color does Alex like?

Type your answer (Red, Blue, or Green):"""

        return Exercise(
            id=str(uuid.uuid4()),
            category='logic',
            type='grid_logic',
            difficulty=difficulty,
            question=question,
            correct_answer='green',
            options=['Red', 'Blue', 'Green'],
            time_limit_seconds=120 + difficulty * 20,
            hints=[
                "Make a table with people, colors, and pets",
                "Use process of elimination",
                "Start with definite facts"
            ]
        )

    async def validate(self, correct_answer: Any, user_answer: Any) -> bool:
        """Validate logic puzzle answer using LLM for semantic understanding"""
        
        # If no LLM client, fall back to exact matching
        if not self.client:
            return str(user_answer).strip().lower() == str(correct_answer).strip().lower()
        
        # Use LLM for semantic validation
        return await self._validate_llm_logic_answer(correct_answer, user_answer)
    
    async def _validate_llm_logic_answer(self, correct_answer: Any, user_answer: Any) -> bool:
        """Validate logic answer using LLM semantic understanding"""
        
        try:
            # Create a validation prompt for LLM
            validation_prompt = [{
                'role': 'system',
                'content': f"""You are a logic puzzle validator. Determine if the user's answer is logically correct for the given question.

User's answer: "{user_answer}"
Correct answer: "{correct_answer}"

Evaluate if the user's answer is semantically equivalent or logically correct compared to the correct answer. Consider:
1. Synonyms and alternative phrasings
2. Logical correctness regardless of exact wording
3. Case insensitivity
4. Common abbreviations or alternative forms

Respond with ONLY "correct" if the answer is logically correct, or "incorrect" if it's wrong."""
            }]
            
            response = await self.client._make_request(
                model=self.client.config.fallback_model,  # Use cheaper model for validation
                messages=validation_prompt,
                temperature=0.1,  # Low temperature for consistent validation
                max_tokens=10
            )
            
            result_text = response['choices'][0]['message']['content'].strip().lower()
            
            logger.debug(
                "llm_validation_result",
                user_answer=user_answer,
                correct_answer=correct_answer,
                llm_result=result_text
            )
            
            return 'incorrect' not in result_text
            
        except Exception as e:
            logger.warning(
                "llm_validation_failed",
                error=str(e),
                falling_back_to_exact_match=True,
                user_answer=user_answer,
                correct_answer=correct_answer
            )
            # Fall back to exact matching if LLM validation fails
            return str(user_answer).strip().lower() == str(correct_answer).strip().lower()


class ProblemSolvingGenerator:
    """Generate problem-solving exercises"""

    def __init__(self, openrouter_client=None):
        self.client = openrouter_client

    async def generate(self, difficulty: int) -> Exercise:
        """Generate problem-solving exercise using LLM with fallback to generic exercises"""

        # If no LLM client, fall back to generic exercises
        if not self.client:
            logger.info("no_llm_client_falling_back_to_generic")
            problem_types = [
                "optimization",
                "resource_allocation",
                "strategy",
                "multi-step"
            ]
            problem_type = random.choice(problem_types)
            return self._generate_generic_fallback_exercise(problem_type, difficulty)

        # Use LLM to generate dynamic exercise
        return await self._generate_llm_exercise(difficulty)

    async def _generate_llm_exercise(self, difficulty: int) -> Exercise:
        """Generate problem-solving exercise using LLM"""

        problem_types = [
            "optimization",
            "resource_allocation",
            "strategy",
            "multi-step"
        ]

        problem_type = random.choice(problem_types)

        try:
            # Generate exercise via LLM
            exercise_data = await self.client.generate_problem_solving_exercise(
                problem_type,
                difficulty
            )

            # Create comprehensive question from scenario and question
            full_question = f"Problem Solving - {problem_type.replace('_', ' ').title()}\n\n"
            full_question += f"Scenario: {exercise_data['scenario']}\n\n"
            full_question += f"Question: {exercise_data['question']}"

            # Create Exercise object from LLM data
            return Exercise(
                id=str(uuid.uuid4()),
                category='problem_solving',
                type=problem_type,
                difficulty=difficulty,
                question=full_question,
                correct_answer=exercise_data['correct_answer'],
                options=exercise_data.get('options'),
                time_limit_seconds=120 + difficulty * 30,
                hints=exercise_data.get('hints', [
                    "Think through the problem step by step",
                    "Consider all available options",
                    "Focus on the key constraints and objectives"
                ])
            )

        except Exception as e:
            logger.warning(
                "llm_problem_solving_generation_failed",
                error=str(e),
                problem_type=problem_type,
                difficulty=difficulty,
                falling_back_to_generic=True
            )
            # Generate a simple fallback exercise directly
            return self._generate_generic_fallback_exercise(problem_type, difficulty)
    
    def _generate_generic_fallback_exercise(self, problem_type: str, difficulty: int) -> Exercise:
        """Generate a simple generic fallback exercise when LLM generation fails"""
        
        # Create a basic question for each problem type
        questions = {
            'optimization': f"Problem Solving - Optimization\n\nFind the optimal solution for this {difficulty}-level optimization problem.",
            'resource_allocation': f"Problem Solving - Resource Allocation\n\nAllocate resources efficiently for this {difficulty}-level scenario.",
            'strategy': f"Problem Solving - Strategy\n\nDevelop the best strategy for this {difficulty}-level challenge.",
            'multi-step': f"Problem Solving - Multi-Step\n\nSolve this {difficulty}-level problem by breaking it down into steps."
        }
        
        question = questions.get(problem_type, questions['optimization'])
        
        return Exercise(
            id=str(uuid.uuid4()),
            category='problem_solving',
            type=problem_type,
            difficulty=difficulty,
            question=question,
            correct_answer="solution",  # Generic answer
            options=None,
            time_limit_seconds=120 + difficulty * 30,
            hints=[
                "Think through the problem step by step",
                "Consider all available options",
                "Focus on the key constraints and objectives"
            ]
        )





    async def validate(self, correct_answer: Any, user_answer: Any) -> bool:
        """Validate problem-solving answer using LLM for semantic understanding when available"""
        
        # If no LLM client, fall back to exact matching
        if not self.client:
            return str(user_answer).strip().lower() == str(correct_answer).strip().lower()
        
        # Use LLM for semantic validation
        return await self._validate_llm_problem_solving_answer(correct_answer, user_answer)
    
    async def _validate_llm_problem_solving_answer(self, correct_answer: Any, user_answer: Any) -> bool:
        """Validate problem-solving answer using LLM semantic understanding"""
        
        try:
            # Create a validation prompt for LLM
            validation_prompt = [{
                'role': 'system',
                'content': f"""You are a problem-solving exercise validator. Determine if the user's answer is logically correct for the given problem type.

User's answer: "{user_answer}"
Correct answer: "{correct_answer}"

Evaluate if the user's answer is semantically equivalent or logically correct compared to the correct answer. Consider:
1. Synonyms and alternative phrasings
2. Logical correctness regardless of exact wording
3. Case insensitivity
4. Numerical answers with different formatting
5. Strategic approaches that achieve the same outcome

Respond with ONLY "correct" if the answer is logically correct, or "incorrect" if it's wrong."""
            }]
            
            response = await self.client._make_request(
                model=self.client.config.fallback_model,  # Use cheaper model for validation
                messages=validation_prompt,
                temperature=0.1,  # Low temperature for consistent validation
                max_tokens=10
            )
            
            result_text = response['choices'][0]['message']['content'].strip().lower()
            
            logger.debug(
                "llm_problem_solving_validation_result",
                user_answer=user_answer,
                correct_answer=correct_answer,
                llm_result=result_text
            )
            
            return 'incorrect' not in result_text
            
        except Exception as e:
            logger.warning(
                "llm_problem_solving_validation_failed",
                error=str(e),
                falling_back_to_exact_match=True,
                user_answer=user_answer,
                correct_answer=correct_answer
            )
            # Fall back to exact matching if LLM validation fails
            return str(user_answer).strip().lower() == str(correct_answer).strip().lower()


class PatternRecognitionGenerator:
    """Generate pattern recognition exercises"""

    def __init__(self, openrouter_client=None):
        self.client = openrouter_client

    async def generate(self, difficulty: int) -> Exercise:
        """Generate pattern recognition exercise using LLM with fallback to LLM-based methods"""

        # If no LLM client, fall back to simple LLM-based generators
        if not self.client:
            exercise_types = [
                self._number_sequence,
                self._analogy,
                self._classification,
                self._visual_pattern,
                self._sequence_completion
            ]
            generator_func = random.choice(exercise_types)
            # For no client case, use sync fallback methods
            if generator_func in [self._visual_pattern, self._sequence_completion]:
                return generator_func(difficulty)
            else:
                # For async methods that need LLM, create simple sync versions
                return self._create_simple_fallback(generator_func.__name__, difficulty)

        # Always attempt LLM generation first
        try:
            return await self._generate_llm_exercise(difficulty)
        except Exception as e:
            logger.warning(
                "llm_generation_failed_falling_back_to_llm_methods",
                error=str(e),
                difficulty=difficulty
            )
            # Fall back to LLM-based methods that don't require client calls
            exercise_types = [
                self._visual_pattern,
                self._sequence_completion
            ]
            generator_func = random.choice(exercise_types)
            return generator_func(difficulty)

    async def _generate_llm_exercise(self, difficulty: int) -> Exercise:
        """Generate pattern recognition exercise using LLM"""

        exercise_types = [
            "number_sequence",
            "analogy",
            "classification",
            "visual_pattern",
            "sequence_completion"
        ]

        exercise_type = random.choice(exercise_types)

        try:
            # Generate exercise via LLM
            exercise_data = await self.client.generate_pattern_recognition_exercise(
                exercise_type,
                difficulty
            )

            # Create Exercise object from LLM data
            return Exercise(
                id=str(uuid.uuid4()),
                category='pattern_recognition',
                type=exercise_type,
                difficulty=difficulty,
                question=exercise_data['question'],
                correct_answer=exercise_data['answer'],
                options=exercise_data.get('options'),
                time_limit_seconds=60 + difficulty * 15,
                hints=exercise_data.get('hints', [
                    "Look for patterns and relationships",
                    "Consider different types of progressions",
                    "Think about the underlying rule"
                ])
            )

        except Exception as e:
            logger.warning(
                "llm_pattern_recognition_generation_failed",
                error=str(e),
                exercise_type=exercise_type,
                difficulty=difficulty,
                falling_back_to_llm_methods=True
            )
            # Fall back to LLM-based methods that don't require client calls
            fallback_methods = {
                'number_sequence': self._number_sequence,
                'analogy': self._analogy,
                'classification': self._classification,
                'visual_pattern': self._visual_pattern,
                'sequence_completion': self._sequence_completion
            }
            return fallback_methods[exercise_type](difficulty)

    def _create_simple_fallback(self, method_name: str, difficulty: int) -> Exercise:
        """Create simple fallback exercise when LLM client is not available"""
        if method_name == "_number_sequence":
            if difficulty <= 2:
                seq = [2, 4, 6, 8, '?']
                answer = '10'
                pattern = 'Add 2'
            elif difficulty <= 4:
                seq = [1, 2, 4, 8, '?']
                answer = '16'
                pattern = 'Multiply by 2'
            else:
                seq = [1, 1, 2, 3, 5, '?']
                answer = '8'
                pattern = 'Fibonacci-like'
            
            question = f"""Pattern Recognition - Number Sequence

What number comes next?

{', '.join([str(x) for x in seq])}

Type your answer (just the number):"""

            return Exercise(
                id=str(uuid.uuid4()),
                category='pattern_recognition',
                type='number_sequence',
                difficulty=difficulty,
                question=question,
                correct_answer=answer,
                options=None,
                time_limit_seconds=60 + difficulty * 15,
                hints=[
                    "Look for arithmetic patterns",
                    "Try differences between numbers",
                    f"Pattern hint: {pattern[:3]}..."
                ]
            )
        
        elif method_name == "_analogy":
            if difficulty <= 2:
                premise = "Hot is to Cold as Up is to ___"
                answer = 'down'
            elif difficulty <= 4:
                premise = "Pen is to Writer as Brush is to ___"
                answer = 'painter'
            else:
                premise = "Book is to Library as Painting is to ___"
                answer = 'gallery'
            
            question = f"""Pattern Recognition - Analogy

Complete the analogy:

{premise}

Type your answer:"""

            return Exercise(
                id=str(uuid.uuid4()),
                category='pattern_recognition',
                type='analogy',
                difficulty=difficulty,
                question=question,
                correct_answer=answer,
                options=None,
                time_limit_seconds=60,
                hints=[
                    "What's the relationship?",
                    "Think about function or purpose",
                    "Consider the context"
                ]
            )
        
        elif method_name == "_classification":
            if difficulty <= 2:
                words = "Apple, Banana, Carrot, Orange, Grape"
                answer = 'carrot'
            elif difficulty <= 4:
                words = "Dog, Cat, Bird, Fish, Tiger"
                answer = 'bird'
            else:
                words = "Car, Boat, Train, Airplane, Bicycle"
                answer = 'bicycle'
            
            question = f"""Pattern Recognition - Classification

Which word doesn't belong?

{words}

Type your answer:"""

            return Exercise(
                id=str(uuid.uuid4()),
                category='pattern_recognition',
                type='classification',
                difficulty=difficulty,
                question=question,
                correct_answer=answer,
                options=None,
                time_limit_seconds=45,
                hints=[
                    "What do most of them have in common?",
                    "Think about categories",
                    "One is different from the others"
                ]
            )
        
        else:
            # Default fallback
            return Exercise(
                id=str(uuid.uuid4()),
                category='pattern_recognition',
                type='pattern_recognition',
                difficulty=difficulty,
                question=f"Pattern Recognition - {method_name.replace('_', ' ').title()}\n\nComplete this {difficulty}-level pattern recognition exercise.",
                correct_answer='answer',
                options=None,
                time_limit_seconds=60 + difficulty * 15,
                hints=[
                    "Look for patterns and relationships",
                    "Consider different types of progressions",
                    "Think about the underlying rule"
                ]
            )

    async def _number_sequence(self, difficulty: int) -> Exercise:
        """Generate number sequence puzzle using LLM fallback"""
        
        try:
            # Use LLM to generate number sequence
            exercise_data = await self.client.generate_pattern_recognition_exercise(
                "number_sequence",
                difficulty
            )
            
            return Exercise(
                id=str(uuid.uuid4()),
                category='pattern_recognition',
                type='number_sequence',
                difficulty=difficulty,
                question=exercise_data['question'],
                correct_answer=exercise_data['answer'],
                options=exercise_data.get('options'),
                time_limit_seconds=60 + difficulty * 15,
                hints=exercise_data.get('hints', [
                    "Look for arithmetic patterns",
                    "Try differences between numbers",
                    "Consider the pattern rule"
                ])
            )
            
        except Exception as e:
            logger.warning(
                "llm_number_sequence_failed",
                error=str(e),
                difficulty=difficulty,
                falling_back_to_simple=True
            )
            # Simple fallback sequence
            if difficulty <= 2:
                seq = [2, 4, 6, 8, '?']
                answer = '10'
                pattern = 'Add 2'
            elif difficulty <= 4:
                seq = [1, 2, 4, 8, '?']
                answer = '16'
                pattern = 'Multiply by 2'
            else:
                seq = [1, 1, 2, 3, 5, '?']
                answer = '8'
                pattern = 'Fibonacci-like'
            
            question = f"""Pattern Recognition - Number Sequence

What number comes next?

{', '.join([str(x) for x in seq])}

Type your answer (just the number):"""

            return Exercise(
                id=str(uuid.uuid4()),
                category='pattern_recognition',
                type='number_sequence',
                difficulty=difficulty,
                question=question,
                correct_answer=answer,
                options=None,
                time_limit_seconds=60 + difficulty * 15,
                hints=[
                    "Look for arithmetic patterns",
                    "Try differences between numbers",
                    f"Pattern hint: {pattern[:3]}..."
                ]
            )

    async def _analogy(self, difficulty: int) -> Exercise:
        """Generate analogy puzzle using LLM fallback"""
        
        try:
            # Use LLM to generate analogy
            exercise_data = await self.client.generate_pattern_recognition_exercise(
                "analogy",
                difficulty
            )
            
            return Exercise(
                id=str(uuid.uuid4()),
                category='pattern_recognition',
                type='analogy',
                difficulty=difficulty,
                question=exercise_data['question'],
                correct_answer=exercise_data['answer'],
                options=exercise_data.get('options'),
                time_limit_seconds=60,
                hints=exercise_data.get('hints', [
                    "What's the relationship?",
                    "Think about function or purpose",
                    "Consider the context"
                ])
            )
            
        except Exception as e:
            logger.warning(
                "llm_analogy_failed",
                error=str(e),
                difficulty=difficulty,
                falling_back_to_simple=True
            )
            # Simple fallback analogy
            if difficulty <= 2:
                premise = "Hot is to Cold as Up is to ___"
                answer = 'down'
            elif difficulty <= 4:
                premise = "Pen is to Writer as Brush is to ___"
                answer = 'painter'
            else:
                premise = "Book is to Library as Painting is to ___"
                answer = 'gallery'
            
            question = f"""Pattern Recognition - Analogy

Complete the analogy:

{premise}

Type your answer:"""

            return Exercise(
                id=str(uuid.uuid4()),
                category='pattern_recognition',
                type='analogy',
                difficulty=difficulty,
                question=question,
                correct_answer=answer,
                options=None,
                time_limit_seconds=60,
                hints=[
                    "What's the relationship?",
                    "Think about function or purpose",
                    "Consider the context"
                ]
            )

    async def _classification(self, difficulty: int) -> Exercise:
        """Generate classification puzzle using LLM fallback"""
        
        try:
            # Use LLM to generate classification
            exercise_data = await self.client.generate_pattern_recognition_exercise(
                "classification",
                difficulty
            )
            
            return Exercise(
                id=str(uuid.uuid4()),
                category='pattern_recognition',
                type='classification',
                difficulty=difficulty,
                question=exercise_data['question'],
                correct_answer=exercise_data['answer'],
                options=exercise_data.get('options'),
                time_limit_seconds=45,
                hints=exercise_data.get('hints', [
                    "What do most of them have in common?",
                    "Think about categories",
                    "One is different from the others"
                ])
            )
            
        except Exception as e:
            logger.warning(
                "llm_classification_failed",
                error=str(e),
                difficulty=difficulty,
                falling_back_to_simple=True
            )
            # Simple fallback classification
            if difficulty <= 2:
                words = "Apple, Banana, Carrot, Orange, Grape"
                answer = 'carrot'
            elif difficulty <= 4:
                words = "Dog, Cat, Bird, Fish, Tiger"
                answer = 'bird'
            else:
                words = "Car, Boat, Train, Airplane, Bicycle"
                answer = 'bicycle'
            
            question = f"""Pattern Recognition - Classification

Which word doesn't belong?

{words}

Type your answer:"""

            return Exercise(
                id=str(uuid.uuid4()),
                category='pattern_recognition',
                type='classification',
                difficulty=difficulty,
                question=question,
                correct_answer=answer,
                options=None,
                time_limit_seconds=45,
                hints=[
                    "What do most of them have in common?",
                    "Think about categories",
                    "One is different from the others"
                ]
            )

    def _visual_pattern(self, difficulty: int) -> Exercise:
        """Generate visual pattern puzzle"""

        patterns = {
            1: {
                'pattern': ['■', '□', '■', '□', '?'],
                'answer': '■',
                'description': 'Alternating filled and empty squares'
            },
            2: {
                'pattern': ['●', '●', '○', '●', '●', '?'],
                'answer': '○',
                'description': 'Two filled, one empty, repeating'
            },
            3: {
                'pattern': ['▲', '■', '●', '▲', '?'],
                'answer': '■',
                'description': 'Shape sequence: triangle, square, circle, repeat'
            },
            4: {
                'pattern': ['A', 'C', 'E', 'G', '?'],
                'answer': 'I',
                'description': 'Skip letters: A, skip B, C, skip D, etc.'
            },
            5: {
                'pattern': ['1', '1', '2', '3', '5', '?'],
                'answer': '8',
                'description': 'Fibonacci sequence with numbers'
            }
        }

        pattern = patterns.get(difficulty, patterns[3])

        question = f"""Pattern Recognition - Visual Pattern

What symbol comes next?

{' '.join(pattern['pattern'])}

Type your answer (just the symbol):"""

        return Exercise(
            id=str(uuid.uuid4()),
            category='pattern_recognition',
            type='visual_pattern',
            difficulty=difficulty,
            question=question,
            correct_answer=pattern['answer'],
            options=None,
            time_limit_seconds=60 + difficulty * 15,
            hints=[
                "Look for repeating sequences",
                "Consider the position in the pattern",
                f"Pattern hint: {pattern['description'][:3]}..."
            ]
        )

    def _sequence_completion(self, difficulty: int) -> Exercise:
        """Generate sequence completion puzzle"""

        sequences = {
            1: {
                'sequence': ['A', 'B', 'D', 'G', '?'],
                'answer': 'K',
                'pattern': 'Add 1, 2, 3, 4 letters (A+1=B, B+2=D, D+3=G, G+4=K)'
            },
            2: {
                'sequence': [2, 6, 18, 54, '?'],
                'answer': '162',
                'pattern': 'Multiply by 3 each time'
            },
            3: {
                'sequence': [1, 4, 9, 16, 25, '?'],
                'answer': '36',
                'pattern': 'Perfect squares (1², 2², 3², 4², 5²)'
            },
            4: {
                'sequence': ['X', 'Y', 'A', 'B', '?'],
                'answer': 'C',
                'pattern': 'Alphabet sequence wrapping around (X,Y then A,B,C)'
            },
            5: {
                'sequence': [1, 1, 2, 3, 5, 8, '?'],
                'answer': '13',
                'pattern': 'Fibonacci sequence (each number is sum of previous two)'
            }
        }

        seq = sequences.get(difficulty, sequences[3])

        question = f"""Pattern Recognition - Sequence Completion

What comes next?

{', '.join([str(x) for x in seq['sequence']])}

Type your answer:"""

        return Exercise(
            id=str(uuid.uuid4()),
            category='pattern_recognition',
            type='sequence_completion',
            difficulty=difficulty,
            question=question,
            correct_answer=seq['answer'],
            options=None,
            time_limit_seconds=60 + difficulty * 15,
            hints=[
                "Look for mathematical relationships",
                "Check for arithmetic progressions",
                f"Pattern hint: {seq['pattern'][:3]}..."
            ]
        )

    async def validate(self, correct_answer: Any, user_answer: Any) -> bool:
        """Validate pattern recognition answer using LLM for semantic understanding"""
        
        # If no LLM client, fall back to exact matching
        if not self.client:
            return str(user_answer).strip().lower() == str(correct_answer).strip().lower()
        
        # Use LLM for semantic validation
        return await self._validate_llm_pattern_answer(correct_answer, user_answer)
    
    async def _validate_llm_pattern_answer(self, correct_answer: Any, user_answer: Any) -> bool:
        """Validate pattern recognition answer using LLM semantic understanding"""
        
        try:
            # Create a validation prompt for LLM
            validation_prompt = [{
                'role': 'system',
                'content': f"""You are a pattern recognition exercise validator. Determine if the user's answer is logically correct for the given pattern.

User's answer: "{user_answer}"
Correct answer: "{correct_answer}"

Evaluate if the user's answer is semantically equivalent or logically correct compared to the correct answer. Consider:
1. Synonyms and alternative phrasings
2. Pattern correctness regardless of exact wording
3. Case insensitivity
4. Numerical answers with different formatting
5. Pattern completion that follows the same rule

Respond with ONLY "correct" if the answer is logically correct, or "incorrect" if it's wrong."""
            }]
            
            response = await self.client._make_request(
                model=self.client.config.fallback_model,  # Use cheaper model for validation
                messages=validation_prompt,
                temperature=0.1,  # Low temperature for consistent validation
                max_tokens=10
            )
            
            result_text = response['choices'][0]['message']['content'].strip().lower()
            
            logger.debug(
                "llm_pattern_validation_result",
                user_answer=user_answer,
                correct_answer=correct_answer,
                llm_result=result_text
            )
            
            return 'incorrect' not in result_text
            
        except Exception as e:
            logger.warning(
                "llm_pattern_validation_failed",
                error=str(e),
                falling_back_to_exact_match=True,
                user_answer=user_answer,
                correct_answer=correct_answer
            )
            # Fall back to exact matching if LLM validation fails
            return str(user_answer).strip().lower() == str(correct_answer).strip().lower()


class AttentionExerciseGenerator:
    """Generate attention and focus exercises using LLM with fallback"""

    def __init__(self, openrouter_client=None):
        self.client = openrouter_client

    async def generate(self, difficulty: int) -> Exercise:
        """Generate attention exercise using LLM with fallback to hardcoded exercises"""

        # If no LLM client, fall back to hardcoded exercises
        if not self.client:
            logger.info("no_llm_client_falling_back_to_hardcoded_attention")
            exercise_types = [
                self._selective_attention_hardcoded,
                self._information_filtering_hardcoded,
                self._focus_challenge_hardcoded
            ]
            generator_func = random.choice(exercise_types)
            return generator_func(difficulty)

        # Use LLM to generate dynamic exercise
        return await self._generate_llm_exercise(difficulty)

    async def _generate_llm_exercise(self, difficulty: int) -> Exercise:
        """Generate attention exercise using LLM"""

        exercise_types = [
            "selective_attention",
            "information_filtering",
            "focus_challenge"
        ]

        exercise_type = random.choice(exercise_types)

        try:
            # Generate exercise via LLM
            exercise_data = await self.client.generate_attention_exercise(
                exercise_type,
                difficulty
            )

            # Create Exercise object from LLM data
            return Exercise(
                id=str(uuid.uuid4()),
                category='attention',
                type=exercise_type,
                difficulty=difficulty,
                question=exercise_data['question'],
                correct_answer=exercise_data['answer'],
                options=exercise_data.get('options'),
                time_limit_seconds=60 + difficulty * 15,
                hints=exercise_data.get('hints', [
                    "Pay close attention to details",
                    "Focus on the specific task",
                    "Avoid distractions"
                ])
            )

        except Exception as e:
            logger.warning(
                "llm_attention_generation_failed",
                error=str(e),
                exercise_type=exercise_type,
                difficulty=difficulty,
                falling_back_to_hardcoded=True
            )
            # Fall back to hardcoded generator
            fallback_methods = {
                'selective_attention': self._selective_attention_hardcoded,
                'information_filtering': self._information_filtering_hardcoded,
                'focus_challenge': self._focus_challenge_hardcoded
            }
            return fallback_methods[exercise_type](difficulty)

    def _selective_attention_hardcoded(self, difficulty: int) -> Exercise:
        """Generate hardcoded selective attention exercise"""
        
        if difficulty <= 2:
            # Simple color and shape task
            question = """Selective Attention Exercise - Color Focus

Read the following list of words and count ONLY the words that are written in RED:

RED, blue, RED, green, RED, blue, green, RED, blue, RED

Type the count of RED words:"""
            correct_answer = "4"
        elif difficulty <= 4:
            # More complex task with mixed attributes
            question = """Selective Attention Exercise - Mixed Attributes

Read the following sequence and count ONLY the numbers that are ODD:

3, red, 8, blue, 5, green, 2, red, 7, blue, 4, green, 9, red

Type the count of odd numbers:"""
            correct_answer = "4"
        else:
            # Complex task with multiple layers
            question = """Selective Attention Exercise - Complex Filtering

Read the following text and identify ALL words that:
1. Are exactly 4 letters long
2. Start with a consonant
3. Are NOT colors

Text: The quick brown fox jumps over the lazy dog. Please help me find these special words.

Type the words separated by commas:"""
            correct_answer = "jumps,help,find,these,words"
        
        return Exercise(
            id=str(uuid.uuid4()),
            category='attention',
            type='selective_attention',
            difficulty=difficulty,
            question=question,
            correct_answer=correct_answer,
            options=None,
            time_limit_seconds=60 + difficulty * 15,  # Consistent with LLM exercises
            hints=[
                "Focus only on the specific criteria mentioned",
                "Ignore all other information",
                "Double-check your count/selection"
            ]
        )

    def _information_filtering_hardcoded(self, difficulty: int) -> Exercise:
        """Generate hardcoded information filtering exercise"""
        
        if difficulty <= 2:
            # Simple relevant vs irrelevant
            question = """Information Filtering Exercise - Relevant Information

You need to plan a beach vacation. Which of these items are RELEVANT to your planning?

Items: swimsuit, umbrella, winter coat, sunscreen, sunglasses, snow boots

Type only the relevant items separated by commas:"""
            correct_answer = "swimsuit,umbrella,sunscreen,sunglasses"
        elif difficulty <= 4:
            # More complex filtering
            question = """Information Filtering Exercise - Business Context

You're analyzing a company's financial report for investment purposes. Which information is MOST RELEVANT for your decision?

Financial Data:
- Revenue: $2.5M (up 15% from last quarter)
- CEO's favorite color: blue
- Operating expenses: $1.8M
- Company founded in 1995
- Net profit: $700K
- Office location: 123 Main Street
- Employee satisfaction: 85%
- Stock price: $45.20 (up 5% today)

Type the 3 most relevant financial metrics:"""
            correct_answer = "revenue,operating expenses,net profit"
        else:
            # Complex multi-step filtering
            question = """Information Filtering Exercise - Multi-Step Analysis

You're researching climate change impacts on agriculture. Filter this information to find ONLY data that:
1. Is from the last 5 years (2019-2024)
2. Relates to crop yields specifically
3. Shows statistical significance

Research Data:
- 2018: Wheat yields decreased by 3% due to drought (p=0.02)
- 2019: Corn yields increased by 8% with new irrigation (p=0.001)
- 2020: Rice yields stable despite floods (p=0.15)
- 2021: Soybean yields decreased by 12% due to heatwave (p<0.001)
- 2022: Overall agricultural output increased by 5% (p=0.08)
- 2023: Wheat yields increased by 7% with climate-resistant seeds (p=0.003)
- 2024: Potato yields decreased by 4% due to unexpected frost (p=0.04)

Type the relevant findings with their significance levels:"""
            correct_answer = "2019:corn yields increased by 8% with new irrigation (p=0.001),2023:wheat yields increased by 7% with climate-resistant seeds (p=0.003),2024:potato yields decreased by 4% due to unexpected frost (p=0.04)"
        
        return Exercise(
            id=str(uuid.uuid4()),
            category='attention',
            type='information_filtering',
            difficulty=difficulty,
            question=question,
            correct_answer=correct_answer,
            options=None,
            time_limit_seconds=60 + difficulty * 15,
            hints=[
                "Focus on the specific filtering criteria",
                "Eliminate information that doesn't match",
                "Be thorough in your analysis"
            ]
        )

    def _focus_challenge_hardcoded(self, difficulty: int) -> Exercise:
        """Generate hardcoded focus challenge exercise"""
        
        if difficulty <= 2:
            # Simple sustained attention task
            question = """Focus Challenge - Sustained Attention

Carefully read the following text and answer the question:

The quick brown fox jumps over the lazy dog. The lazy dog barks at the quick brown fox. The fox runs away from the barking dog.

Question: How many times does the word "dog" appear in the text?

Type your answer:"""
            correct_answer = "2"
        elif difficulty <= 4:
            # More complex focus task with distractions
            question = """Focus Challenge - Resistance to Distractions

Ignore the words in parentheses and count only the bolded words:

**The** (quick) **brown** (fox) **jumps** (over) **the** (lazy) **dog**. **The** (quick) **brown** (fox) **runs** (away) **from** (the) **barking** (dog).

Question: How many bolded words are there?

Type your answer:"""
            correct_answer = "8"
        else:
            # Complex focus challenge with time pressure
            question = """Focus Challenge - Complex Pattern Recognition

Study this sequence for 30 seconds, then answer without looking back:

Sequence: A-1, B-2, C-3, D-4, E-5, F-6, G-7, H-8, I-9, J-10

Now, answer these questions:
1. What letter corresponds to number 7?
2. What number corresponds to letter D?
3. What is the sum of all numbers?
4. How many vowels are in the sequence?

Type your answers separated by commas:"""
            correct_answer = "G,4,55,3"
        
        return Exercise(
            id=str(uuid.uuid4()),
            category='attention',
            type='focus_challenge',
            difficulty=difficulty,
            question=question,
            correct_answer=correct_answer,
            options=None,
            time_limit_seconds=30 + difficulty * 10,
            hints=[
                "Maintain focus throughout the task",
                "Ignore irrelevant information",
                "Work systematically through the questions"
            ]
        )

    async def validate(self, correct_answer: Any, user_answer: Any) -> bool:
        """Validate attention exercise answer using LLM with fallback to exact matching"""
        
        # If no LLM client, fall back to exact matching
        if not self.client:
            return str(user_answer).strip().lower() == str(correct_answer).strip().lower()
        
        # Use LLM for semantic validation
        return await self._validate_llm_attention_answer(correct_answer, user_answer)
    
    async def _validate_llm_attention_answer(self, correct_answer: Any, user_answer: Any) -> bool:
        """Validate attention answer using LLM semantic understanding"""
        
        try:
            # Create a validation prompt for LLM
            validation_prompt = [{
                'role': 'system',
                'content': f"""You are an attention exercise validator. Determine if the user's answer is logically correct for the given attention exercise.

User's answer: "{user_answer}"
Correct answer: "{correct_answer}"

Evaluate if the user's answer is semantically equivalent or logically correct compared to the correct answer. Consider:
1. Synonyms and alternative phrasings
2. Numerical answers with different formatting
3. Case insensitivity
4. For attention exercises: focus on whether the core requirement is met
5. For information filtering: whether key information is identified regardless of exact wording

Respond with ONLY "correct" if the answer is logically correct, or "incorrect" if it's wrong."""
            }]
            
            response = await self.client._make_request(
                model=self.client.config.fallback_model,  # Use cheaper model for validation
                messages=validation_prompt,
                temperature=0.1,  # Low temperature for consistent validation
                max_tokens=10
            )
            
            result_text = response['choices'][0]['message']['content'].strip().lower()
            
            logger.debug(
                "llm_attention_validation_result",
                user_answer=user_answer,
                correct_answer=correct_answer,
                llm_result=result_text
            )
            
            return 'incorrect' not in result_text
            
        except Exception as e:
            logger.warning(
                "llm_attention_validation_failed",
                error=str(e),
                falling_back_to_exact_match=True,
                user_answer=user_answer,
                correct_answer=correct_answer
            )
            # Fall back to exact matching if LLM validation fails
            return str(user_answer).strip().lower() == str(correct_answer).strip().lower()


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
            'attention': AttentionExerciseGenerator()
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
            # Exact match for sequences and numbers
            return str(user_answer).strip() == str(correct_answer).strip()


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
    """Generate attention and focus exercises"""

    async def generate(self, difficulty: int) -> Exercise:
        """Generate attention exercise"""

        exercise_types = [
            self._selective_attention,
            self._information_filtering,
            self._focus_challenge
        ]

        generator_func = random.choice(exercise_types)
        return generator_func(difficulty)

    def _selective_attention(self, difficulty: int) -> Exercise:
        """Generate selective attention exercise"""

        # Generate text with specific words to find
        distractors = ["the", "and", "but", "for", "with", "from", "about"]
        targets = ["focus", "attention", "concentrate"]

        # Build sentence
        words = []
        target_count = difficulty + 2
        for i in range(target_count):
            words.extend(random.sample(distractors, 3))
            words.append(random.choice(targets))

        text = ' '.join(words)

        question = f"""Attention Exercise - Selective Attention

Count how many times the word "focus" appears in the following text:

{text}

Type your answer (just the number):"""

        correct_count = text.lower().count('focus')

        return Exercise(
            id=str(uuid.uuid4()),
            category='attention',
            type='selective_attention',
            difficulty=difficulty,
            question=question,
            correct_answer=str(correct_count),
            options=None,
            time_limit_seconds=60 + difficulty * 10,
            hints=[
                "Read carefully",
                "Don't count similar words",
                "Read through twice to verify"
            ]
        )

    def _information_filtering(self, difficulty: int) -> Exercise:
        """Generate information filtering exercise"""

        # Present mixed relevant and irrelevant information
        question = f"""Attention Exercise - Information Filtering

Read this scenario and identify the KEY information:

"Sarah needs to attend a meeting at 2 PM. She likes coffee. The meeting is in Room 304. Her favorite color is blue. She needs to bring the Q3 report. The weather is sunny. The report is on her desk."

What are the 3 essential pieces of information for the meeting? (separate with commas)

Example format: time, location, item"""

        return Exercise(
            id=str(uuid.uuid4()),
            category='attention',
            type='information_filtering',
            difficulty=difficulty,
            question=question,
            correct_answer='2 pm, room 304, q3 report',
            options=None,
            time_limit_seconds=90,
            hints=[
                "What's directly relevant to the meeting?",
                "Ignore personal preferences",
                "Focus on actionable information"
            ]
        )

    def _focus_challenge(self, difficulty: int) -> Exercise:
        """Generate focus challenge"""

        # Create a simple math problem with distractors
        num1 = random.randint(10, 50)
        num2 = random.randint(10, 50)
        num3 = random.randint(1, 10)

        question = f"""Attention Exercise - Focus Challenge

Calculate: ({num1} + {num2}) × {num3}

But first, ignore this distraction:
- The sky is blue
- 2 + 2 = 4
- Elephants are large

Now solve: ({num1} + {num2}) × {num3} = ?

Type your answer (just the number):"""

        correct_answer = (num1 + num2) * num3

        return Exercise(
            id=str(uuid.uuid4()),
            category='attention',
            type='focus_challenge',
            difficulty=difficulty,
            question=question,
            correct_answer=str(correct_answer),
            options=None,
            time_limit_seconds=60,
            hints=[
                "Follow order of operations",
                "Ignore the distractors",
                "Calculate step by step"
            ]
        )

    async def validate(self, correct_answer: Any, user_answer: Any) -> bool:
        """Validate attention exercise answer"""
        # For information filtering, check if key terms are present
        if isinstance(correct_answer, str) and ',' in correct_answer:
            correct_terms = set(correct_answer.lower().split(','))
            user_terms = set(str(user_answer).lower().split(','))
            # Accept if at least 2 out of 3 key terms are present
            matches = len(correct_terms.intersection(user_terms))
            return matches >= 2

        return str(user_answer).strip().lower() == str(correct_answer).strip().lower()


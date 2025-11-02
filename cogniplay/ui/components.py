from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(show_settings: bool = True) -> InlineKeyboardMarkup:
    """Build the Main Menu keyboard.

    Args:
        show_settings: Whether to include the Settings button row.
    """
    keyboard = [
        [InlineKeyboardButton("🎯 Start Training", callback_data='train')],
        [InlineKeyboardButton("📊 View Progress", callback_data='progress')],
    ]
    if show_settings:
        keyboard.append([InlineKeyboardButton("⚙️ Settings", callback_data='settings')])
    keyboard.append([InlineKeyboardButton("❓ Help", callback_data='help')])
    return InlineKeyboardMarkup(keyboard)


def training_menu_keyboard() -> InlineKeyboardMarkup:
    """Build the Training mode selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("🧩 Cognitive Exercises", callback_data='mode_exercise')],
        [InlineKeyboardButton("🎭 Role-Playing Scenarios", callback_data='mode_scenario')],
        [InlineKeyboardButton("🎯 Full Session", callback_data='mode_full')],
        [InlineKeyboardButton("« Back", callback_data='back_main')],
    ]
    return InlineKeyboardMarkup(keyboard)


def exercise_category_keyboard() -> InlineKeyboardMarkup:
    """Build the Exercise category selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("🧠 Memory Games", callback_data='cat_memory')],
        [InlineKeyboardButton("🔍 Logic Puzzles", callback_data='cat_logic')],
        [InlineKeyboardButton("💡 Problem Solving", callback_data='cat_problem_solving')],
        [InlineKeyboardButton("🎨 Pattern Recognition", callback_data='cat_pattern_recognition')],
        [InlineKeyboardButton("👁️ Attention Tasks", callback_data='cat_attention')],
        [InlineKeyboardButton("🎲 Random", callback_data='cat_random')],
        [InlineKeyboardButton("« Back", callback_data='back_train')],
    ]
    return InlineKeyboardMarkup(keyboard)


def scenario_type_keyboard() -> InlineKeyboardMarkup:
    """Build the Scenario type selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("🤝 Negotiation", callback_data='scen_negotiation')],
        [InlineKeyboardButton("🔧 Problem Solving", callback_data='scen_problem_solving')],
        [InlineKeyboardButton("💬 Social Interaction", callback_data='scen_social_interaction')],
        [InlineKeyboardButton("👔 Leadership", callback_data='scen_leadership')],
        [InlineKeyboardButton("💡 Creative Thinking", callback_data='scen_creative_thinking')],
        [InlineKeyboardButton("« Back", callback_data='back_train')],
    ]
    return InlineKeyboardMarkup(keyboard)


def _summarize_action_label(action: str, max_len: int = 18) -> str:
    """Create a short, verb-first label for an action.

    Heuristic:
    - Take the first clause up to punctuation.
    - Keep the first 2–4 words, trimmed to max_len.
    - Prefer not to append ellipsis on the button; full text will appear in the message body.
    """
    if not action:
        return "Option"
    # Split on common punctuation to get the first clause
    clause = action.split(";")[0].split(".")[0].split(":")[0].split("–")[0].split("-")[0]
    words = clause.strip().split()
    if not words:
        words = action.strip().split()
    # Keep first few words to form a concise label
    short = " ".join(words[:4])
    # Trim to max length without breaking mid-word if possible
    if len(short) > max_len:
        short = short[:max_len].rstrip()
    return short


def format_actions_list(actions: List[str]) -> str:
    """Return a numbered list of full action texts for inclusion in the message body."""
    lines = [f"{i+1}. {a}" for i, a in enumerate(actions[:3])]
    return "\n".join(lines)


def scenario_action_keyboard(actions: List[str], include_custom: bool = True) -> InlineKeyboardMarkup:
    """Build the scenario actions keyboard from a list of action strings.

    Uses short, verb-like labels on buttons and shows full text in the message body.
    Shows up to 3 actions (to match current UX), plus optional custom action.
    """
    keyboard = []
    for i, action in enumerate(actions[:3]):
        summary = _summarize_action_label(action)
        label = f"{i+1}. {summary}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"action_{i}")])
    if include_custom:
        keyboard.append([InlineKeyboardButton("✍️ Custom Action", callback_data='custom_action')])
    return InlineKeyboardMarkup(keyboard)


def error_main_menu_text(base_message: str) -> str:
    """Standardize error text that returns the user to main menu."""
    return (
        f"{base_message}\n\n"
        "Returning to main menu. What would you like to do?"
    )


def format_scenario_intro(title: str, context: str, characters: List[dict], initial_situation: str) -> str:
    """Format scenario introduction text.

    Kept identical to previous inline formatting in main.py.
    """
    characters_text = "\n".join([
        f"• {char['name']} - {char['role']}" for char in characters
    ])
    text = (
        f"🎬 {title}\n\n"
        f"📖 Context:\n{context}\n\n"
        f"👥 Characters:\n{characters_text}\n\n"
        f"🎭 Situation:\n{initial_situation}\n\n"
        f"What do you do?"
    )
    return text

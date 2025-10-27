# CogniPlay - Personal Cognitive Training Platform

🧠 **CogniPlay** is a comprehensive Telegram bot for personal cognitive training, featuring adaptive difficulty, AI-powered role-playing scenarios, and detailed progress analytics.

## Features

### 🧩 Cognitive Exercises
- **5 Exercise Categories**: Memory, Logic, Problem Solving, Pattern Recognition, Attention
- **Adaptive Difficulty**: 5 levels that adjust based on performance (3 consecutive successes/failures)
- **Real-time Feedback**: Immediate scoring and improvement suggestions

### 🎭 AI Role-Playing Scenarios
- **Interactive Characters**: AI-generated personalities with consistent behavior
- **Multiple Scenario Types**: Negotiation, Problem Solving, Social Interaction, Leadership, Creative Thinking
- **Decision Quality Scoring**: AI evaluates decision-making effectiveness

### 📊 Advanced Analytics
- **Progress Tracking**: 7/30/90-day performance reports
- **Trend Analysis**: Identify improving/stable/declining performance
- **Personalized Recommendations**: AI-generated training suggestions
- **Category Performance**: Detailed breakdown by exercise type

### ⚙️ Smart Difficulty Adjustment
- **3-Consecutive Rule**: Automatic level changes based on performance patterns
- **Performance Thresholds**: ≥90% accuracy for success, <50% for difficulty reduction
- **Manual Override**: Administrative difficulty adjustments

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         TELEGRAM API                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    PRESENTATION LAYER                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Telegram Bot Handler (python-telegram-bot)     │  │
│  │  - Webhook/Polling Manager                                │  │
│  │  - Command Handlers (/start, /train, /progress, /help)   │  │
│  │  - Message Router                                          │  │
│  │  - Conversation State Manager                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      APPLICATION LAYER                           │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │  Training Manager   │  │    Analytics Manager            │  │
│  │  - Session Control  │  │    - Performance Calculation    │  │
│  │  - Exercise Flow    │  │    - Trend Analysis             │  │
│  │  - Scenario Flow    │  │    - Report Generation          │  │
│  └─────────┬───────────┘  └─────────────────────────────────┘  │
│            │                                                     │
│  ┌─────────▼─────────────────────────────────────────────────┐ │
│  │           Difficulty Adjustment Engine                     │ │
│  │           - Performance Tracking                           │ │
│  │           - Level Calculation                              │ │
│  │           - Threshold Monitoring (3 consecutive rule)      │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                       BUSINESS LOGIC LAYER                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  Cognitive       │  │  Role-Playing    │  │  Feedback    │  │
│  │  Exercise Engine │  │  Scenario Engine │  │  Generator   │  │
│  │  - Memory Games  │  │  - AI Characters │  │  - Scoring   │  │
│  │  - Logic Puzzles │  │  - Narrative     │  │  - Insights  │  │
│  │  - Pattern Recog │  │    Branching     │  │  - Recommen- │  │
│  │  - Problem Solve │  │  - Context Mgmt  │  │    dations   │  │
│  │  - Attention     │  │  - Consistency   │  │  - Motivation│  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      INTEGRATION LAYER                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              AI Service Integration                       │  │
│  │  ┌────────────────────┐  ┌──────────────────────────┐   │  │
│  │  │ OpenRouter Client  │  │  Character Generator     │   │  │
│  │  │ - API Interface    │  │  - Personality Traits    │   │  │
│  │  │ - Model Selection  │  │  - Dialogue Generation   │   │  │
│  │  │ - Prompt Builder   │  │  - Consistency Manager   │   │  │
│  │  │ - Response Parser  │  │  - Memory Context        │   │  │
│  │  │ - Error Handling   │  │  - Emotion Tracking      │   │  │
│  │  └────────────────────┘  └──────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                         DATA LAYER                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  User Repository │  │  Session Repo    │  │  Progress    │  │
│  │  - User Profile  │  │  - Session Data  │  │  Repository  │  │
│  │  - Settings      │  │  - State Mgmt    │  │  - Metrics   │  │
│  │  - Auth Data     │  │  - History       │  │  - Trends    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐│
│  │  Exercise Repo   │  │  In-Memory State Cache               ││
│  │  - Templates     │  │  - Active Session                    ││
│  │  - Difficulty    │  │  - Scenario Context                  ││
│  │  - Categories    │  │  - Conversation State                ││
│  └──────────────────┘  └──────────────────────────────────────┘│
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      PERSISTENCE LAYER                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   SQLite Database                         │  │
│  │  File: cogniplay.db                                       │  │
│  │                                                          │  │
│  │  Tables:                                                 │  │
│  │  - user_profile                                          │  │
│  │  - sessions                                              │  │
│  │  - exercise_results                                      │  │
│  │  - scenario_results                                      │  │
│  │  - user_progress                                         │  │
│  │  - difficulty_tracking                                   │  │
│  │  - ai_character_memory                                    │  │
│  │  - exercise_templates                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

- **Python 3.11+**: Core language
- **python-telegram-bot 20.x**: Telegram bot framework
- **SQLite3**: Embedded database with WAL mode
- **SQLAlchemy 2.x**: ORM with connection pooling
- **OpenRouter API**: Unified AI model access (Claude 3.5 Sonnet primary)
- **httpx**: Async HTTP client
- **Pydantic**: Data validation and settings
- **structlog**: Structured logging

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd cogniplay
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

5. **Run the bot:**
   ```bash
   python -m cogniplay.main
   ```

## Configuration

### Environment Variables (.env)

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_USER_ID=your_telegram_user_id

# OpenRouter API Configuration
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_PRIMARY_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_FALLBACK_MODEL=anthropic/claude-3-haiku

# Database Configuration
DATABASE_PATH=./data/cogniplay.db

# Application Configuration
LOG_LEVEL=INFO
SESSION_TIMEOUT_MINUTES=30
MAX_RESPONSE_TIME_SECONDS=3

# Feature Flags
ENABLE_ANALYTICS=true
ENABLE_DIFFICULTY_ADJUSTMENT=true
DIFFICULTY_ADJUSTMENT_THRESHOLD=3

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_INTERVAL_HOURS=24
```

### Getting API Keys

1. **Telegram Bot Token:**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Use `/newbot` command
   - Follow the setup instructions

2. **OpenRouter API Key:**
   - Sign up at [OpenRouter.ai](https://openrouter.ai)
   - Generate an API key in your dashboard
   - Recommended models: `anthropic/claude-3.5-sonnet`

## Usage

### Basic Commands

- `/start` - Initialize bot and view main menu
- `/train` - Start a training session
- `/progress` - View detailed progress analytics
- `/stats` - Quick performance statistics
- `/difficulty` - View current difficulty level
- `/help` - Show available commands and features

### Training Modes

1. **Cognitive Exercises:**
   - Choose from 5 categories: Memory, Logic, Problem Solving, Pattern Recognition, Attention
   - Difficulty adjusts automatically based on performance
   - Real-time feedback and scoring

2. **Role-Playing Scenarios:**
   - Interactive AI characters with personality
   - Multiple scenario types for different skills
   - Decision quality evaluation

3. **Full Sessions:**
   - Combination of exercises and scenarios
   - Comprehensive training experience

### Progress Tracking

- **Real-time Analytics:** Immediate performance feedback
- **Trend Analysis:** 7/30/90-day progress reports
- **Personalized Recommendations:** AI-generated improvement suggestions
- **Category Breakdown:** Performance analysis by exercise type

## Database Schema

The application uses SQLite with the following tables:

- `user_profile`: Single-user profile and settings
- `sessions`: Training session tracking
- `exercise_results`: Individual exercise performance
- `scenario_results`: Scenario interaction outcomes
- `user_progress`: Aggregated daily progress
- `difficulty_tracking`: Consecutive performance monitoring
- `ai_character_memory`: Character consistency and history
- `exercise_templates`: Predefined exercise configurations

## Development

### Project Structure

```
cogniplay/
├── bot/
│   ├── handlers/          # Telegram message handlers
│   ├── middleware/        # Logging and error handling
│   └── formatters/        # Response formatting
├── core/                  # Business logic managers
│   ├── training_manager.py
│   ├── analytics_manager.py
│   └── difficulty_engine.py
├── engines/               # Exercise and scenario engines
│   ├── exercise_engine.py
│   └── scenario_engine.py
├── integrations/          # External API clients
│   ├── openrouter_client.py
│   └── character_generator.py
├── data/                  # Data access layer
│   ├── models.py          # Data models
│   └── repositories/      # Repository pattern implementation
├── database/              # Database connection and schema
├── config/                # Configuration management
└── utils/                 # Utility functions
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

- **Type Hints:** Full type annotation throughout
- **Docstrings:** Comprehensive documentation
- **Error Handling:** Graceful failure with user feedback
- **Logging:** Structured logging with context

## Performance Optimization

- **Response Time Target:** <3 seconds for all interactions
- **Database Optimization:** WAL mode, indexes, prepared statements
- **Caching:** In-memory state for active sessions
- **Async Operations:** Non-blocking API calls and database operations
- **Connection Pooling:** Efficient database connection management

## Security

- **Single-User Design:** Private bot for individual use
- **Input Validation:** Pydantic models for all inputs
- **API Key Protection:** Environment variable storage
- **SQL Injection Prevention:** Parameterized queries
- **Error Sanitization:** No sensitive data in error messages

## Monitoring & Observability

- **Structured Logging:** JSON format with context
- **Performance Metrics:** Response times and API usage
- **Error Tracking:** Comprehensive error logging
- **Usage Analytics:** Token consumption and cost tracking

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the `/help` command in the bot
- Review the logs for error details
- Ensure all environment variables are properly configured

## Roadmap

- [ ] Multi-user support
- [ ] Additional exercise categories
- [ ] Advanced scenario branching
- [ ] Mobile app companion
- [ ] Integration with external cognitive assessment tools
- [ ] Group training sessions
- [ ] Advanced analytics dashboard

---

**CogniPlay** - Train your mind, track your progress, achieve your cognitive potential! 🧠✨

# CogniPlay - Personal Cognitive Training Platform

🧠 **CogniPlay** is a comprehensive Telegram bot for personal cognitive training, featuring adaptive difficulty, AI-powered role-playing scenarios, and detailed progress analytics.

![](docs/intro.png)

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

## Quick Start

### Using Makefile (Recommended)

The easiest way to get started:

```bash
# Setup virtual environment and install dependencies
make setup

# Run locally
make run

# Deploy to server
make start

# Stop server
make stop
```

### Manual Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd tele-cogni-play
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   venv/bin/pip3 install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

5. **Run the bot:**
   ```bash
   ./venv/bin/python3 -m cogniplay.main
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
DATABASE_PATH=./data/tele-cogni-play.db

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

### Server Deployment

```bash
# Deploy and start on server
make start

# Stop server deployment
make stop

# SSH to server for manual management
make ssh
```

The deployment uses screen sessions for persistent running:

- **Screen session name:** `tele-cogni-play`
- **Virtual environment:** `venv` in project root
- **Python executable:** `venv/bin/python3 -m cogniplay.main`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

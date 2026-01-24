cd $1 || exit
uv sync --no-dev
bash ./scripts/start_screen.sh tele-cogni-play 'uv run python -m cogniplay.main'
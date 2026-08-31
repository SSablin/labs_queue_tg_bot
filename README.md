Labs Queue Telegram Bot

Overview

This repository contains a Telegram bot for managing a lab queue. The bot uses aiogram for Telegram interactions, asyncpg for PostgreSQL access, and gspread (Google Sheets) for storing queue data.

Environment variables and configuration

The application expects configuration in config.py. The following environment variables / configuration items are required:

- BOT_TOKEN: Telegram Bot API token (string)
- DB_CONFIG: dict with keys: user, password, database, host, optional port (int)
  Example in config.py (not committed):
  DB_CONFIG = {
      "user": "postgres",
      "password": "secret",
      "database": "mydb",
      "host": "localhost",
      "port": 5432,
  }
- CREDITS_PATH: file system path to Google service account JSON file (service account key)
- SHEET_URL: Google Sheets URL or ID used by the bot
- PROXY: Optional HTTP proxy for aiohttp session (optional)

Security notes

Do NOT commit service account JSON files or any secrets to the repository. Keep credentials secure (use environment variables, secret managers or GitHub Secrets for CI). If a service account key has been committed, rotate it immediately and remove the file from the repository history.

Running locally

1. Create a Python virtual environment and activate it:
   python3 -m venv .venv
   source .venv/bin/activate

2. Install runtime dependencies (project-specific). If the project contains requirements.txt, install it. Otherwise, ensure required packages are installed:
   pip install -r requirements.txt

3. Provide required configuration in config.py or via environment variables. Ensure CREDITS_PATH points to a valid Google service account JSON with appropriate scopes.

4. Run the bot:
   python main.py

Testing

Unit tests are provided using pytest and pytest-asyncio. The test suite uses light test stubs (tests/conftest.py) so installing the full aiogram/asyncpg stack is not required for unit tests.

1. Create and activate your virtual environment (see above), then install dev dependencies:
   pip install -r requirements-dev.txt

2. Run tests:
   pytest -q

Continuous Integration

A GitHub Actions workflow is included (.github/workflows/ci.yml) that runs pytest on push and pull requests.
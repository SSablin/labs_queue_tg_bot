import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Config:
    bot_token: str
    db_user: str
    db_password: str
    db_name: str
    db_host: str
    db_port: int
    proxy: str | None
    credits_path: str
    sheet_url: str


def load_config() -> Config:
    """Load and validate application configuration explicitly."""
    return Config(
        bot_token=_require("BOT_TOKEN"),
        db_user=_require("DB_USER"),
        db_password=_require("DB_PASSWORD"),
        db_name=_require("DB_NAME"),
        db_host=_require("DB_HOST"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        proxy=os.getenv("PROXY"),
        credits_path=_require("CREDITS_PATH"),
        sheet_url=_require("SHEET_URL"),
    )

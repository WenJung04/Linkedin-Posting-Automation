import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ["TELEGRAM_BOT_TOKEN", "ALLOWED_TELEGRAM_USER_ID", "GEMINI_API_KEY"]


@dataclass(frozen=True)
class Config:
    telegram_token: str
    allowed_user_id: int
    gemini_api_key: str
    gemini_model: str
    data_dir: Path
    style_dir: Path


def load_config() -> Config:
    load_dotenv(PROJECT_ROOT / ".env")
    missing = [name for name in REQUIRED if not os.getenv(name)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}. See .env.example.")
    try:
        allowed_user_id = int(os.environ["ALLOWED_TELEGRAM_USER_ID"])
    except ValueError:
        raise SystemExit("ALLOWED_TELEGRAM_USER_ID must be a number.")

    return Config(
        telegram_token=os.environ["TELEGRAM_BOT_TOKEN"],
        allowed_user_id=allowed_user_id,
        gemini_api_key=os.environ["GEMINI_API_KEY"],
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        data_dir=PROJECT_ROOT / "data",
        style_dir=PROJECT_ROOT / "style_samples",
    )


def load_style_samples(style_dir: Path) -> list[str]:
    files = sorted(style_dir.glob("*.txt"))
    return [f.read_text(encoding="utf-8") for f in files]

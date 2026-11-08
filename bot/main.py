import logging

from bot.config import load_config
from bot.handlers import build_application


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)  # hides URLs containing the bot token
    build_application(load_config()).run_polling()


if __name__ == "__main__":
    main()

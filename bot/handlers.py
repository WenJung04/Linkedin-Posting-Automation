"""Telegram handlers. Thin layer: reads/writes the Store, uses session.py for state rules."""

import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bot.config import Config, load_style_samples
from bot.db import Store
from bot.factcheck import unsupported_facts
from bot.llm import DraftModel, GeminiModel
from bot.prompt import X_MAX_CHARS, DraftInputs, DraftParseError, build_draft_prompt, parse_draft_response
from bot.session import (
    ASKING,
    DRAFTABLE_STATUSES,
    QUESTIONS,
    Session,
    SessionError,
    can_capture,
    cancel,
    clean_event_name,
    current_question,
    finish_capture,
    mark_drafted,
    normalize_answer,
    record_answer,
)

logger = logging.getLogger(__name__)

MAX_PHOTOS_TO_MODEL = 6
DRAFT_TIMEOUT_SECONDS = 240  # free-tier Gemini takes roughly 45-135s per draft

HELP = (
    "/event <name> - start capturing an event\n"
    "Then send notes and photos as they happen.\n"
    "/done - answer 3 quick questions and get your drafts\n"
    "/redraft - regenerate the latest drafts\n"
    "/cancel - drop the open event"
)


def _store(context: ContextTypes.DEFAULT_TYPE) -> Store:
    return context.bot_data["store"]


async def _ack(update: Update) -> None:
    try:
        await update.message.set_reaction("👍")
    except Exception:  # reactions can fail in some chats; not worth bothering the user
        logger.debug("Could not set reaction", exc_info=True)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP)


async def event_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    store = _store(context)
    active = store.active_session()
    if active:
        await update.message.reply_text(
            f"'{active.name}' is still open. /done to finish it or /cancel to drop it."
        )
        return
    try:
        name = clean_event_name(" ".join(context.args))
    except SessionError as exc:
        await update.message.reply_text(str(exc))
        return
    store.create_event(name)
    await update.message.reply_text(
        f"Capturing '{name}'. Send notes and photos as they happen. /done when you're finished."
    )


async def done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    store = _store(context)
    session = store.active_session()
    if session is None:
        await update.message.reply_text("No event open. Start one with /event <name>.")
        return
    if session.status == ASKING:
        await update.message.reply_text(current_question(session)[1])
        return

    session = finish_capture(session)
    store.save_session(session)
    notes, photos = store.capture_counts(session.event_id)
    await update.message.reply_text(
        f"Got {notes} notes and {photos} photos. {len(QUESTIONS)} quick questions, "
        "reply 'skip' to any of them."
    )
    await update.message.reply_text(current_question(session)[1])


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    store = _store(context)
    session = store.active_session()
    if session is None:
        await update.message.reply_text("Nothing to cancel.")
        return
    store.save_session(cancel(session))
    await update.message.reply_text(f"Dropped '{session.name}'.")


async def redraft_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = _store(context).latest_session()
    if session is None or session.status not in DRAFTABLE_STATUSES:
        await update.message.reply_text("Nothing to redraft yet. Finish an event with /done first.")
        return
    await _generate_and_send(update, context, session)


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    store = _store(context)
    session = store.active_session()
    if session is None:
        await update.message.reply_text("No event open. Start one with /event <name>.")
        return

    if can_capture(session):
        store.add_note(session.event_id, update.message.text)
        await _ack(update)
        return

    key, _ = current_question(session)
    store.save_answer(session.event_id, key, normalize_answer(update.message.text))
    session = record_answer(session)
    store.save_session(session)
    next_question = current_question(session)
    if next_question:
        await update.message.reply_text(next_question[1])
    else:
        await _generate_and_send(update, context, session)


async def photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    store = _store(context)
    session = store.active_session()
    if session is None:
        await update.message.reply_text(
            "No event open, so the photo wasn't saved. Start one with /event <name>, "
            "then send it again."
        )
        return
    if not can_capture(session):
        await update.message.reply_text(
            "You're answering questions now, so the photo wasn't saved. "
            "Reply to the question above (or 'skip')."
        )
        return

    photo = update.message.photo[-1]  # largest size Telegram kept
    config: Config = context.bot_data["config"]
    path = config.data_dir / "photos" / str(session.event_id) / f"{photo.file_unique_id}.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    telegram_file = await photo.get_file()
    await telegram_file.download_to_drive(path)
    store.add_photo(session.event_id, update.message.caption or "", path)
    await _ack(update)


async def _generate_and_send(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session: Session
) -> None:
    store = _store(context)
    config: Config = context.bot_data["config"]
    model: DraftModel = context.bot_data["model"]

    notes = store.notes(session.event_id)
    photos = store.photos(session.event_id)[:MAX_PHOTOS_TO_MODEL]
    answers = store.answers(session.event_id)
    inputs = DraftInputs(
        event_name=session.name,
        notes=notes,
        photo_captions=[caption for _, caption in photos],
        answers=answers,
        style_samples=load_style_samples(config.style_dir),
    )

    await update.message.reply_text("Drafting... this usually takes about a minute.")
    try:
        raw = await asyncio.wait_for(
            model.generate(build_draft_prompt(inputs), [path for path, _ in photos]),
            DRAFT_TIMEOUT_SECONDS,
        )
        draft = parse_draft_response(raw, len(photos))
    except TimeoutError:
        logger.warning("Draft generation timed out")
        await update.message.reply_text("Gemini took too long to answer. Try /redraft.")
        return
    except DraftParseError:
        logger.exception("Could not parse draft")
        await update.message.reply_text("The draft came back malformed. Try /redraft.")
        return
    except Exception:
        logger.exception("Draft generation failed")
        await update.message.reply_text(
            "Drafting failed (Gemini busy or free-tier limit). Try /redraft in a minute. "
            "Details are in the bot's terminal."
        )
        return

    store.save_draft(session.event_id, draft)
    store.save_session(mark_drafted(session))

    await update.message.reply_text(
        "Drafts below, one per message so they're easy to copy: "
        "short LinkedIn, long LinkedIn, then X."
    )
    for text in (draft.short, draft.long, draft.x_post):
        await update.message.reply_text(text)

    if draft.best_photo:
        best_path = photos[draft.best_photo - 1][0]
        with best_path.open("rb") as photo_file:
            await update.message.reply_photo(
                photo_file,
                caption=f"Suggested photo: {draft.best_photo_reason}\n"
                "Get consent before posting anyone's face.",
            )

    source = "\n".join(
        [session.name, *notes, *inputs.photo_captions, *(a for a in answers.values() if a)]
    )
    checks = []
    flagged = unsupported_facts("\n".join([draft.short, draft.long, draft.x_post]), source)
    if flagged:
        checks.append("Not in your notes, double-check: " + ", ".join(flagged))
    if len(draft.x_post) > X_MAX_CHARS:
        checks.append(f"X post is {len(draft.x_post)} chars, over the {X_MAX_CHARS} limit.")
    if not inputs.style_samples:
        checks.append("No style samples found, so the voice is generic. Add .txt files to style_samples/.")
    checks.append("Not happy? /redraft")
    await update.message.reply_text("\n".join(checks))


def build_application(config: Config) -> Application:
    app = Application.builder().token(config.telegram_token).build()
    app.bot_data["config"] = config
    app.bot_data["store"] = Store(config.data_dir / "bot.sqlite3")
    app.bot_data["model"] = GeminiModel(config.gemini_api_key, config.gemini_model)

    only_me = filters.User(user_id=config.allowed_user_id)
    app.add_handler(CommandHandler(["start", "help"], start_cmd, filters=only_me))
    app.add_handler(CommandHandler("event", event_cmd, filters=only_me))
    app.add_handler(CommandHandler("done", done_cmd, filters=only_me))
    app.add_handler(CommandHandler("cancel", cancel_cmd, filters=only_me))
    app.add_handler(CommandHandler("redraft", redraft_cmd, filters=only_me))
    app.add_handler(MessageHandler(only_me & filters.TEXT & ~filters.COMMAND, text_message))
    app.add_handler(MessageHandler(only_me & filters.PHOTO, photo_message))
    return app

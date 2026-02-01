"""
Telegram-бот для абитуриентов магистратур ИТМО: «Искусственный интеллект» и «AI-продукты и технологии».
Отвечает только на релевантные вопросы по этим программам; помогает выбрать программу и дисциплины.
"""
import logging

from telegram import Update
from telegram.helpers import escape_markdown
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from .config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY
from .knowledge import is_relevant, answer_from_knowledge
from .recommendations import recommend_program, recommend_electives

if OPENAI_API_KEY:
    from .llm import is_relevant_llm, generate_answer_rag
    from .rag import has_index, build_index, retrieve
    from .history import get_history_for_prompt, save_turn
else:
    is_relevant_llm = None
    generate_answer_rag = None
    has_index = None
    build_index = None
    retrieve = None
    get_history_for_prompt = None
    save_turn = None

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

USER_STATE: dict[int, str] = {}


def get_state(user_id: int) -> str:
    return USER_STATE.get(user_id, "")


def set_state(user_id: int, state: str) -> None:
    if state:
        USER_STATE[user_id] = state
    else:
        USER_STATE.pop(user_id, None)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    set_state(update.effective_user.id, "")
    text = (
        "Привет! Я помогаю абитуриентам разобраться с магистратурами ИТМО:\n"
        "• **Искусственный интеллект** (abit.itmo.ru/program/master/ai)\n"
        "• **AI-продукты и технологии** (abit.itmo.ru/program/master/ai_product)\n\n"
        "Могу ответить на вопросы по программам, поступлению, учебным планам и карьере. "
        "Отвечаю только на вопросы, связанные с этими двумя магистратурами.\n\n"
        "Команды:\n"
        "/program — подобрать программу под ваш бэкграунд\n"
        "/electives — подобрать выборные дисциплины (сначала выберите программу)\n"
        "Или просто напишите вопрос — например: «Чем отличаются программы?», «Как поступить?»"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_program(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    set_state(update.effective_user.id, "await_program_background")
    await update.message.reply_text(
        "Опишите коротко ваш бэкграунд: образование, опыт, чем занимаетесь и что хотите развивать "
        "(например: «Программист, хочу углубиться в ML» или «Менеджер продукта, хочу работать с AI»). "
        "По этому я подберу программу."
    )


async def cmd_electives(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    set_state(update.effective_user.id, "await_program_id")
    await update.message.reply_text(
        "Для подбора выборных дисциплин укажите программу:\n"
        "• Напишите **ai** — для программы «Искусственный интеллект»\n"
        "• Напишите **ai_product** — для программы «AI-продукты и технологии»"
    )


async def handle_program_id(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    tid = update.effective_user.id
    t = text.strip().lower()
    if t in ("ai", "искусственный интеллект", "ии"):
        context.user_data["electives_program_id"] = "ai"
        set_state(tid, "await_electives_background")
        await update.message.reply_text(
            "Выбрана программа «Искусственный интеллект». "
            "Опишите коротко ваш бэкграунд и что хотите углубить (например: «Backend, хочу MLOps и данные»)."
        )
        return True
    if t in ("ai_product", "ai продукт", "продукты"):
        context.user_data["electives_program_id"] = "ai_product"
        set_state(tid, "await_electives_background")
        await update.message.reply_text(
            "Выбрана программа «AI-продукты и технологии». "
            "Опишите коротко ваш бэкграунд и интересы (например: «Менеджер, хочу стратегию и метрики»)."
        )
        return True
    return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()
    if not text:
        return

    state = get_state(user_id)

    if state == "await_program_id":
        if await handle_program_id(update, context, text):
            pass
        else:
            await update.message.reply_text("Напишите **ai** или **ai_product**.", parse_mode="Markdown")
        return

    if state == "await_program_background":
        set_state(user_id, "")
        reply = recommend_program(text)
        await update.message.reply_text(escape_markdown(reply, version=1), parse_mode="Markdown")
        return

    if state == "await_electives_background":
        set_state(user_id, "")
        program_id = context.user_data.get("electives_program_id", "ai")
        reply = recommend_electives(program_id, text)
        await update.message.reply_text(escape_markdown(reply, version=1), parse_mode="Markdown")
        return

    use_rag = bool(OPENAI_API_KEY and is_relevant_llm and generate_answer_rag)
    if use_rag:
        if not is_relevant_llm(text):
            await update.message.reply_text(
                "Я отвечаю только на вопросы, связанные с магистратурами ИТМО «Искусственный интеллект» и «AI-продукты и технологии»: "
                "поступление, учебные планы, карьера, выбор программы и дисциплин. Задайте, пожалуйста, такой вопрос "
                "или используйте /program и /electives для подбора."
            )
            return
        if not has_index():
            await update.message.reply_text("Строю индекс в Qdrant, подождите несколько секунд…")
            build_index()
            if not has_index():
                await update.message.reply_text(
                    "Не удалось построить индекс. Убедитесь, что в папке data/ есть .md файлы "
                    "(запустите: python run_scraper.py) и что Qdrant запущен."
                )
                return
        rag_context = retrieve(text)
        history_str = get_history_for_prompt(user_id) if get_history_for_prompt else ""
        reply = generate_answer_rag(text, rag_context, history_str)
        if save_turn:
            save_turn(user_id, text, reply)
    else:
        if not is_relevant(text):
            await update.message.reply_text(
                "Я отвечаю только на вопросы, связанные с магистратурами ИТМО «Искусственный интеллект» и «AI-продукты и технологии»: "
                "поступление, учебные планы, карьера, выбор программы и дисциплин. Задайте, пожалуйста, такой вопрос "
                "или используйте /program и /electives для подбора."
            )
            return
        reply = answer_from_knowledge(text)
    # Экранируем Markdown в динамических ответах (LLM/база знаний), чтобы не ломать парсер Telegram
    await update.message.reply_text(escape_markdown(reply, version=1), parse_mode="Markdown")


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Укажите TELEGRAM_BOT_TOKEN в переменных окружения или в .env")
        return
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("program", cmd_program))
    app.add_handler(CommandHandler("electives", cmd_electives))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

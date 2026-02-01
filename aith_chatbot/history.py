"""
Хранение истории диалога через LangChain: последние 2–3 обмена с суммаризацией старых сообщений.
"""
import logging

try:
    from langchain.memory import ConversationSummaryBufferMemory
except ImportError:
    from langchain_community.memory import ConversationSummaryBufferMemory  # noqa: F401

from langchain_openai import ChatOpenAI

from .config import CHAT_MODEL

logger = logging.getLogger(__name__)

# Память на пользователя (user_id -> ConversationSummaryBufferMemory)
_user_memories: dict[int, ConversationSummaryBufferMemory] = {}

# Лимит токенов в буфере до суммаризации; оставляем ~2–3 последних обмена
MAX_TOKEN_LIMIT = 400


def _get_llm() -> ChatOpenAI:
    """LLM для суммаризации и для памяти."""
    return ChatOpenAI(model=CHAT_MODEL, temperature=0)


def get_memory(user_id: int) -> ConversationSummaryBufferMemory:
    """
    Возвращает память диалога для пользователя.
    Хранит последние сообщения и суммаризирует старые при переполнении.
    """
    if user_id not in _user_memories:
        _user_memories[user_id] = ConversationSummaryBufferMemory(
            llm=_get_llm(),
            max_token_limit=MAX_TOKEN_LIMIT,
            return_messages=False,
            memory_key="history",
        )
    return _user_memories[user_id]


def get_history_for_prompt(user_id: int) -> str:
    """
    Возвращает строку истории (суммаризация + последние 2–3 обмена) для вставки в промпт.
    Вызывать до добавления текущего сообщения пользователя.
    """
    memory = get_memory(user_id)
    try:
        vars_ = memory.load_memory_variables({})
        return (vars_.get("history") or "").strip()
    except Exception as e:
        logger.warning("Ошибка загрузки истории для user_id=%s: %s", user_id, e)
        return ""


def save_turn(user_id: int, user_message: str, assistant_message: str) -> None:
    """Сохраняет один обмен (вопрос пользователя и ответ ассистента) в историю."""
    memory = get_memory(user_id)
    try:
        memory.save_context(
            {"input": user_message},
            {"output": assistant_message},
        )
    except Exception as e:
        logger.warning("Ошибка сохранения истории для user_id=%s: %s", user_id, e)

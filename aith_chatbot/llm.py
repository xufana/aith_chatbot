"""
LLM: проверка релевантности вопроса и генерация ответа по контексту (RAG).
"""
import logging
import os
from typing import Optional

from openai import OpenAI

from .config import CHAT_MODEL

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY не задан")
        _client = OpenAI(api_key=key)
    return _client


RELEVANCE_SYSTEM = """Ты классификатор. Твоя задача — определить, относится ли вопрос пользователя к двум магистерским программам ИТМО:
1) «Искусственный интеллект» (abit.itmo.ru/program/master/ai)
2) «AI-продукты и технологии» (abit.itmo.ru/program/master/ai_product)

Релевантные темы: поступление, экзамены, учебные планы, дисциплины, карьера после выпуска, сравнение программ, форма обучения, диплом, стипендии, выбор программы или дисциплин — всё, что касается именно этих двух программ ИТМО.

Нерелевантно: другие вузы, погода, общие вопросы не про эти программы, оффтоп.

Ответь строго одним словом: RELEVANT или IRRELEVANT. Никаких пояснений."""


ANSWER_SYSTEM = """Ты помощник для абитуриентов магистратур ИТМО. Отвечаешь только на основе приведённого ниже контекста о двух программах: «Искусственный интеллект» и «AI-продукты и технологии». Отвечай кратко, по делу, на русском. Если в контексте нет информации для ответа — так и скажи. Не придумывай факты. Можно использовать маркдаун для списков и выделения."""


def generate_answer_rag_with_history(
    question: str,
    context: str,
    history_str: str = "",
) -> str:
    """
    Генерирует ответ по контексту (RAG) и истории диалога (последние 2–3 обмена с суммаризацией).
    history_str — строка из LangChain ConversationSummaryBufferMemory (суммаризация + недавние сообщения).
    """
    system = ANSWER_SYSTEM
    parts = [f"Контекст из базы знаний:\n{context}"] if context.strip() else []
    if history_str.strip():
        parts.append(f"Предыдущий диалог (кратко):\n{history_str}")
    parts.append(f"Текущий вопрос пользователя: {question}")
    user_content = "\n\n".join(parts)
    try:
        client = _get_client()
        r = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1024,
            temperature=0.3,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning("Ошибка LLM при генерации ответа с историей: %s", e)
        return (
            "Не удалось сформировать ответ. Попробуйте позже или переформулируйте вопрос."
        )


def is_relevant_llm(question: str) -> bool:
    """
    Определяет релевантность вопроса через LLM.
    Возвращает True, если вопрос относится к двум магистратурам ИТМО (AI / AI Product).
    """
    question = (question or "").strip()
    if len(question) < 2:
        return False
    try:
        client = _get_client()
        r = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": RELEVANCE_SYSTEM},
                {"role": "user", "content": question},
            ],
            max_tokens=20,
            temperature=0,
        )
        content = (r.choices[0].message.content or "").strip().upper()
        return "RELEVANT" in content
    except Exception as e:
        logger.warning("Ошибка LLM при проверке релевантности: %s", e)
        return False


def generate_answer_rag(question: str, context: str, history_str: str = "") -> str:
    """
    Генерирует ответ на вопрос по контексту (RAG) и опционально по истории диалога.
    Контекст — релевантные фрагменты базы знаний.
    history_str — строка истории (суммаризация + последние обмены) из LangChain.
    """
    if not context.strip() and not history_str.strip():
        return (
            "По вашему вопросу в базе знаний не нашлось подходящих фрагментов. "
            "Попробуйте переформулировать или задать вопрос про поступление, учебные планы или карьеру по программам «Искусственный интеллект» и «AI-продукты и технологии»."
        )
    return generate_answer_rag_with_history(question, context, history_str)

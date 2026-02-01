"""
База знаний и проверка релевантности вопросов.
Бот отвечает только на вопросы, относящиеся к двум магистратурам ИТМО: AI и AI Product.
"""
import json
import re
from typing import Optional

from .config import DATA_DIR

# Ключевые слова релевантности: магистратура, программа, поступление, учебный план и т.д.
RELEVANT_KEYWORDS = [
    "магистратур", "магистерск", "итмо", "itmo", "поступлен", "экзамен", "учебн", "план", "дисциплин",
    "программ", "искусственн", "интеллект", "ai ", "ии ", "ml ", "data ", "product", "продукт",
    "карьер", "бюджет", "контракт", "стипенди", "выпускн", "диплом", "очн", "дистанц",
    "выборн", "выбор", "курс", "предмет", "семестр", "роль", "engineer", "analyst", "manager",
    "рекомендац", "подходит", "разниц", "отличи", "как поступить", "что изучать",
]

# Слова, указывающие на нерелевантность (другие вузы, темы вне обучения)
IRRELEVANT_PATTERNS = [
    r"\b(мгу|спбгу|вышка|hse|мфти)\b",
    r"\b(погода|курс\s+валют|рецепт)\b",
]


def load_programs() -> list[dict]:
    """Загружает данные программ из data/programs.json."""
    path = DATA_DIR / "programs.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_knowledge() -> dict:
    """Загружает сжатый текст для ответов из data/knowledge.json."""
    path = DATA_DIR / "knowledge.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_relevant(user_text: str) -> bool:
    """
    Определяет, относится ли вопрос к магистратурам ИТМО (AI / AI Product).
    Возвращает True только для релевантных вопросов.
    """
    text = user_text.lower().strip()
    if len(text) < 3:
        return False
    for pattern in IRRELEVANT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    for kw in RELEVANT_KEYWORDS:
        if kw in text:
            return True
    if any(x in text for x in ["чем отлич", "какая разниц", "что лучше", "какую программу", "куда поступить"]):
        return True
    return False


def get_context_for_answer(program_ids: Optional[list[str]] = None) -> str:
    """Собирает текстовый контекст из базы знаний для ответа (все программы или выбранные)."""
    knowledge = load_knowledge()
    programs_text = knowledge.get("programs_text", {})
    if program_ids:
        parts = [programs_text.get(pid, "") for pid in program_ids if pid in programs_text]
    else:
        parts = list(programs_text.values())
    return "\n\n".join(parts)


def answer_from_knowledge(question: str, context: Optional[str] = None) -> str:
    """
    Формирует ответ по базе знаний без LLM: поиск по ключевым словам и шаблонам.
    Если передан context — использует его, иначе загружает полный контекст.
    """
    programs = load_programs()
    if context is None:
        context = get_context_for_answer()
    q = question.lower()

    if any(x in q for x in ["чем отлич", "разниц", "различие", "какая программа лучше"]):
        ai = next((p for p in programs if p["id"] == "ai"), None)
        ap = next((p for p in programs if p["id"] == "ai_product"), None)
        if ai and ap:
            return (
                "Кратко о различиях:\n\n"
                "• **Искусственный интеллект** — упор на технические роли: ML Engineer, Data Engineer, "
                "AI Product Developer, Data Analyst. Много математики и ML, инженерия данных, научная траектория. "
                "Подойдёт тем, кто хочет разрабатывать модели и системы.\n\n"
                "• **AI-продукты и технологии** — упор на продуктовые роли: AI Product Manager, AI Project Manager, "
                "Product Data Analyst. Менеджмент продукта, метрики, UX/UI, работа с заказчиками. "
                "Подойдёт тем, кто хочет управлять AI-продуктами и выводить их на рынок.\n\n"
                "Обе программы дают техническую базу по ML и данным; разница в фокусе: разработка vs продукт и менеджмент."
            )

    if any(x in q for x in ["поступлен", "как поступить", "экзамен", "вступительн"]):
        return (
            "Поступление в обе магистратуры возможно несколькими путями:\n"
            "• Вступительный экзамен (дистанционно, 100 баллов). Документы — через личный кабинет абитуриента.\n"
            "• Junior ML Contest — конкурс проектов или курс My First Data Project.\n"
            "• Олимпиады: Я-профессионал, МегаОлимпиада ИТМО, МегаШкола ИТМО.\n"
            "• Конкурс «Портфолио» ИТМО — мотивационное письмо, резюме, достижения; победитель от 85 баллов.\n"
            "• Рекомендательное письмо от руководителя программы.\n\n"
            "Подробности и даты: abit.itmo.ru (раздел магистратура, страницы программ)."
        )

    if any(x in q for x in ["учебн", "план", "дисциплин", "что изучать", "курс", "предмет"]):
        parts = []
        for p in programs:
            cur = p.get("curriculum", {})
            mand = cur.get("mandatory", [])
            elect = cur.get("elective_blocks", {})
            parts.append(
                f"**{p['name']}**\n"
                f"Обязательные: {', '.join(mand[:5])}{'...' if len(mand) > 5 else ''}\n"
                f"Блоки выборных: {', '.join(elect.keys())}."
            )
        return "\n\n".join(parts) if parts else "Учебные планы загружены в бота; уточните, какую программу имеете в виду — «Искусственный интеллект» или «AI-продукты»."

    if any(x in q for x in ["карьер", "работа", "зарплат", "роль"]):
        parts = [f"**{p['name']}**: {p.get('career', '')}" for p in programs]
        return "\n\n".join(parts)

    if any(x in q for x in ["очно", "дистанц", "форма", "как учат"]):
        return (
            "Обе программы — очная форма, но занятия в основном дистанционно. "
            "Очно: BootCamp в начале сентября (обязательно), возможны хакатоны и интенсивы. "
            "Удобно совмещать с работой (вечернее время для программы «Искусственный интеллект»)."
        )

    if any(x in q for x in ["диплом", "выпускн"]):
        return (
            "По окончании выдаётся диплом государственного образца очной магистратуры с квалификацией «Магистр». "
            "Формы выпускной работы: проект для компании-партнёра, научная статья, AI-стартап, образовательный продукт/курс на основе ИИ."
        )

    return (
        "Я помогаю с вопросами по двум магистратурам ИТМО: «Искусственный интеллект» и «AI-продукты и технологии». "
        "Можете спросить: чем программы отличаются, как поступить, что в учебном плане, карьера после выпуска, "
        "или попросить подобрать программу и выборные дисциплины под ваш бэкграунд. Задайте вопрос?"
    )

"""
Рекомендации: выбор программы и выборных дисциплин с учётом бэкграунда абитуриента.
"""
from .knowledge import load_programs


def recommend_program(background: str) -> str:
    """
    Рекомендует одну из двух программ (AI vs AI Product) по текстовому описанию бэкграунда.
    """
    background_lower = background.lower()
    programs = load_programs()
    ai = next((p for p in programs if p["id"] == "ai"), None)
    ai_product = next((p for p in programs if p["id"] == "ai_product"), None)
    if not ai or not ai_product:
        return "Не удалось загрузить данные программ. Попробуйте позже."

    tech_ml_signals = [
        "программист", "разработчик", "developer", "engineer", "ml", "машинное обучение",
        "data science", "дата саентист", "нейросет", "python", "модел", "алгоритм",
        "backend", "фронтенд", "инженер", "математик", "статистик", "исследователь",
    ]
    product_signals = [
        "менеджер", "manager", "продукт", "product", "проект", "project", "аналитик",
        "бизнес", "маркетинг", "ux", "ui", "заказчик", "управлен", "стратеги",
    ]

    tech_score = sum(1 for s in tech_ml_signals if s in background_lower)
    product_score = sum(1 for s in product_signals if s in background_lower)

    if product_score > tech_score:
        return (
            f"С учётом вашего бэкграунда логичнее рассмотреть программу **«{ai_product['name']}»** "
            f"({ai_product['url']}). Она ориентирована на роли AI Product Manager, AI Project Manager, "
            "Product Data Analyst и сочетает технические знания по ИИ с продуктовым менеджментом. "
            "Можете уточнить интересы — подберу выборные дисциплины."
        )
    if tech_score > product_score:
        return (
            f"С учётом вашего бэкграунда хорошо подойдёт программа **«{ai['name']}»** "
            f"({ai['url']}). Она даёт углублённую техническую подготовку: ML Engineer, Data Engineer, "
            "AI Product Developer, Data Analyst, плюс научная траектория. Напишите, что хотите углубить — "
            "подберу выборные курсы."
        )
    return (
        "По вашему описанию подходят обе программы.\n\n"
        f"• **«{ai['name']}»** — если хотите больше разработки моделей и инженерии данных.\n"
        f"• **«{ai_product['name']}»** — если интереснее продуктовый менеджмент и вывод AI-продуктов на рынок.\n\n"
        "Напишите, что важнее: техника (ML, данные) или продукт и управление — подскажу точнее и подберу дисциплины."
    )


def recommend_electives(program_id: str, background: str) -> str:
    """
    Рекомендует выборные дисциплины в рамках выбранной программы с учётом бэкграунда.
    program_id: 'ai' или 'ai_product'
    """
    programs = load_programs()
    program = next((p for p in programs if p["id"] == program_id), None)
    if not program:
        return "Программа не найдена. Укажите: «Искусственный интеллект» (ai) или «AI-продукты и технологии» (ai_product)."
    cur = program.get("curriculum", {})
    blocks = cur.get("elective_blocks", {})
    if not blocks:
        return f"У программы «{program['name']}» в базе нет детализации выборных блоков. Обязательные дисциплины: " + ", ".join(cur.get("mandatory", []))

    background_lower = background.lower()
    recommended = []

    if program_id == "ai":
        if any(x in background_lower for x in ["продукт", "product", "менеджер", "бизнес"]):
            recommended.extend(blocks.get("Продукт и аналитика", [])[:2])
        if any(x in background_lower for x in ["модел", "ml", "алгоритм", "нейросет", "research"]):
            recommended.extend(blocks.get("ML и модели", [])[:2])
        if any(x in background_lower for x in ["данн", "data", "инженер", "пайплайн", "продакшен"]):
            recommended.extend(blocks.get("Данные и инженерия", [])[:2])
        if any(x in background_lower for x in ["наук", "статья", "публикац", "исследован"]):
            recommended.extend(blocks.get("Научная траектория", [])[:2])
        if not recommended:
            recommended = (
                blocks.get("ML и модели", [])[:1] +
                blocks.get("Данные и инженерия", [])[:1] +
                blocks.get("Продукт и аналитика", [])[:1]
            )
    else:
        if any(x in background_lower for x in ["стратеги", "бизнес", "монетизац", "заказчик"]):
            recommended.extend(blocks.get("Продукт и стратегия", [])[:2])
        if any(x in background_lower for x in ["технолог", "ml", "разработ", "аналитик", "a/b"]):
            recommended.extend(blocks.get("Технологии", [])[:2])
        if any(x in background_lower for x in ["данн", "data", "дашборд", "отчёт"]):
            recommended.extend(blocks.get("Данные", [])[:2])
        if not recommended:
            recommended = (
                blocks.get("Продукт и стратегия", [])[:1] +
                blocks.get("Технологии", [])[:1] +
                blocks.get("Данные", [])[:1]
            )

    recommended = list(dict.fromkeys(recommended))[:5]
    return (
        f"Рекомендуемые выборные дисциплины по программе **«{program['name']}»** с учётом вашего бэкграунда:\n\n"
        + "\n".join(f"• {c}" for c in recommended)
        + "\n\nОстальные выборные блоки и дисциплины можно посмотреть в учебном плане на странице программы."
    )

# Чат-бот для абитуриентов магистратур ИТМО (AI и AI Product)

Диалоговый бот помогает абитуриенту разобраться, какая из двух магистерских программ ему подходит и как спланировать учёбу, исходя из учебных планов и описаний программ, загруженных со страниц:

- [Искусственный интеллект](https://abit.itmo.ru/program/master/ai)
- [AI-продукты и технологии](https://abit.itmo.ru/program/master/ai_product)

Реализовано:

1. **Парсинг данных с сайтов** — скрипт `scraper.py` загружает HTML страниц магистратур, конвертирует их в **Markdown** (html2text) и сохраняет в `data/ai.md`, `data/ai_product.md`. RAG строит чанки из этих .md файлов.
2. **Диалоговая система** — Telegram-бот отвечает на вопросы по программам, поступлению, учебным планам и карьере; отвечает **только на релевантные** вопросы по этим двум магистратурам.
3. **Рекомендации** — подбор программы (AI vs AI Product) по бэкграунду абитуриента и рекомендация выборных дисциплин с учётом бэкграунда и выбранной программы.
4. **RAG + LLM** (при заданном `OPENAI_API_KEY`): релевантность определяет LLM; эмбеддинги хранятся в **Qdrant**, поиск по векторам, ответ через GPT. **История диалога** через **LangChain** (ConversationSummaryBufferMemory): последние 2–3 обмена в буфере, старые сообщения суммаризируются и передаются в промпт LLM.

---

## Как решали задачу

- **Парсинг:** `requests` + `BeautifulSoup` + **html2text** — загрузка HTML, конвертация в Markdown, сохранение в `data/*.md`. Рекомендации и fallback-ответы используют `data/programs.json` и `data/knowledge.json`.
- **Релевантность:** при наличии `OPENAI_API_KEY` релевантность определяет LLM (один вызов с промптом «RELEVANT / IRRELEVANT»). Без ключа используется проверка по ключевым словам в `knowledge.py`.
- **Ответы:** при наличии `OPENAI_API_KEY` используется RAG: из Markdown в `data/*.md` чанки строятся через **RecursiveCharacterTextSplitter**, эмбеддинги в **Qdrant**, контекст + **история диалога** (LangChain ConversationSummaryBufferMemory: суммаризация старых сообщений + последние 2–3 обмена) передаются в `gpt-4o-mini`. Без ключа — ответы по правилам и шаблонам из `knowledge.py`.
- **Рекомендации программы:** в `recommendations.py` по тексту бэкграунда считаются «технические» (программист, ML, инженер) и «продуктовые» (менеджер, продукт, UX) сигналы; в зависимости от баланса предлагается программа «Искусственный интеллект» или «AI-продукты и технологии».
- **Рекомендации дисциплин:** по выбранной программе и бэкграунду выбираются блоки выборных курсов (например, при интересе к MLOps — блок «Данные и инженерия» в программе AI) и выдаётся короткий список дисциплин.

---

## Инструменты и зависимости

- **Python 3.10+** (рекомендуется 3.12; в проекте указан `.python-version`)
- **uv** — менеджер зависимостей и окружения (опционально; зависимости заданы в `pyproject.toml`)
- `requests`, `beautifulsoup4`, `html2text` — парсинг HTML → Markdown
- `python-telegram-bot` (v20+) — Telegram Bot API
- `python-dotenv` — переменные окружения
- `openai`, `numpy`, `qdrant-client`, `langchain`, `langchain-openai`, `langchain-community`, `langchain-text-splitters` — RAG, LLM, история диалога (ConversationSummaryBufferMemory)

---

## Запуск

1. Клонируйте репозиторий и перейдите в каталог проекта.

2. Установите зависимости через **uv** (рекомендуется):

   ```bash
   uv sync
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

   Либо без uv:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   После активации окружения все команды (`python scraper.py`, `python bot.py` и т.д.) выполняйте из этого же терминала.

3. Создайте бота в Telegram через [@BotFather](https://t.me/BotFather), скопируйте токен.

4. Создайте файл `.env` (по образцу `.env.example`):

   ```
   TELEGRAM_BOT_TOKEN=ваш_токен
   OPENAI_API_KEY=ваш_ключ_openai   # для RAG и LLM
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   QDRANT_COLLECTION=aith_chatbot
   ```

   Без `OPENAI_API_KEY` бот работает в режиме правил и шаблонов (релевантность по ключевым словам, ответы из базы знаний).

5. Для режима RAG запустите **Qdrant** (векторная БД для эмбеддингов):

   ```bash
   docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant
   ```

   Либо используйте [Qdrant Cloud](https://cloud.qdrant.io/) и укажите в `.env` хост и порт (или URL).

6. Для режима RAG загрузите страницы программ в Markdown (обязательно при первом запуске):

   ```bash
   source .venv/bin/activate
   python run_scraper.py
   ```

   Будут созданы `data/ai.md` и `data/ai_product.md` (парсинг через html2text). Затем соберите индекс в Qdrant:

   ```bash
   python run_build_rag_index.py
   ```

   Иначе индекс будет собран при первом вопросе пользователя (если .md файлы уже есть).

8. Запустите бота:

   ```bash
   python run_bot.py
   ```

В Telegram: команды `/start`, `/program`, `/electives` и произвольные вопросы по двум магистратурам.

---

## Запуск через Docker

Собрать и запустить Qdrant и бота одной командой:

1. Создайте `.env` (по образцу `.env.example`), укажите `TELEGRAM_BOT_TOKEN` и при необходимости `OPENAI_API_KEY`.

2. Убедитесь, что в `data/` есть `programs.json`, `knowledge.json` и при использовании RAG — `ai.md`, `ai_product.md` (выполните локально `python scraper.py` перед сборкой образа, если нужно).

3. Запуск:

   ```bash
   docker compose up -d
   ```

   Бот подключается к Qdrant по имени сервиса `qdrant` (в compose задано `QDRANT_HOST=qdrant`). Для RAG после первого запуска индекс можно собрать при первом вопросе пользователя или один раз выполнить сборку индекса вручную (см. ниже).

---

## Структура проекта

```
aith_chatbot/              # корень репозитория
├── aith_chatbot/          # пакет
│   ├── __init__.py
│   ├── config.py         # конфигурация (токены, пути, Qdrant)
│   ├── knowledge.py      # база знаний, релевантность (fallback)
│   ├── llm.py            # LLM: релевантность и генерация ответа
│   ├── rag.py            # RAG: data/*.md → RecursiveCharacterTextSplitter, Qdrant
│   ├── recommendations.py # рекомендации программы и дисциплин
│   ├── bot.py            # Telegram-бот
│   ├── history.py        # история диалога (LangChain ConversationSummaryBufferMemory)
│   └── scraper.py        # парсинг HTML → Markdown
├── run_bot.py            # точка входа: запуск бота
├── run_scraper.py        # точка входа: парсинг страниц
├── run_build_rag_index.py # точка входа: сборка индекса RAG
├── data/
│   ├── programs.json
│   ├── knowledge.json
│   ├── ai.md
│   └── ai_product.md
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── .python-version
├── .env.example
└── README.md
```

---

## Ссылка на решение

Открытый репозиторий с решением можно выложить на GitHub/GitLab и указать ссылку здесь, например:

- **Репозиторий:** `https://github.com/ваш-логин/aith_chatbot`

Либо выложить архив (ZIP) с проектом и добавить сюда ссылку на архив.

После публикации замените этот блок на актуальную ссылку.

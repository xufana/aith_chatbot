# Конфигурация чат-бота магистратур ИТМО
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Корень проекта (родитель каталога пакета aith_chatbot)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROGRAMS_JSON = DATA_DIR / "programs.json"
KNOWLEDGE_JSON = DATA_DIR / "knowledge.json"

# Токен бота Telegram (обязательно)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# OpenAI API для RAG и LLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# RAG
RAG_TOP_K = 5
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
CHAT_MODEL = "gpt-4o-mini"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "aith_chatbot")

# URL страниц магистратур для парсинга
URL_AI = "https://abit.itmo.ru/program/master/ai"
URL_AI_PRODUCT = "https://abit.itmo.ru/program/master/ai_product"

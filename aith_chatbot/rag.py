"""
RAG: загрузка Markdown из data/*.md, разбиение RecursiveCharacterTextSplitter,
эмбеддинги в Qdrant, поиск по релевантности.
"""
import logging
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .config import (
    DATA_DIR,
    RAG_TOP_K,
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)

logger = logging.getLogger(__name__)

_openai_client = None
_qdrant_client: Optional[QdrantClient] = None


def _get_openai_client():
    import os
    from openai import OpenAI
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY не задан")
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=key)
    return _openai_client


def get_qdrant_client() -> QdrantClient:
    """Клиент Qdrant (host:port или url)."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _qdrant_client


def _load_md_sources() -> list[tuple[str, str]]:
    """
    Загружает все .md файлы из data/.
    Возвращает список (content, source_id), где source_id — имя файла без расширения.
    """
    sources = []
    if not DATA_DIR.exists():
        return sources
    for path in sorted(DATA_DIR.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
            source_id = path.stem
            if content.strip():
                sources.append((content.strip(), source_id))
        except Exception as e:
            logger.warning("Не удалось прочитать %s: %s", path, e)
    return sources


def build_chunks() -> list[dict]:
    """
    Строит чанки из Markdown-файлов в data/*.md с помощью RecursiveCharacterTextSplitter.
    Каждый чанк: {"text": str, "source": str (program id из имени файла)}.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    sources = _load_md_sources()
    if not sources:
        logger.warning("Нет .md файлов в %s. Запустите scraper.", DATA_DIR)
        return []
    chunks = []
    for content, source_id in sources:
        for piece in splitter.split_text(content):
            piece = piece.strip()
            if piece:
                chunks.append({"text": piece, "source": source_id})
    logger.info("Построено %d чанков из %d источников", len(chunks), len(sources))
    return chunks


def get_embedding(text: str) -> list[float]:
    """Получить эмбеддинг текста через OpenAI API."""
    client = _get_openai_client()
    r = client.embeddings.create(model=EMBEDDING_MODEL, input=text.strip()[:8000])
    return r.data[0].embedding


def ensure_collection() -> None:
    """Создаёт коллекцию в Qdrant, если её ещё нет."""
    client = get_qdrant_client()
    collections = client.get_collections().collections
    if any(c.name == QDRANT_COLLECTION for c in collections):
        return
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )
    logger.info("Коллекция Qdrant создана: %s", QDRANT_COLLECTION)


def build_index(force: bool = False) -> int:
    """
    Строит индекс: чанки + эмбеддинги, сохраняет в Qdrant.
    Если force=True — пересоздаёт коллекцию и заново загружает точки.
    Возвращает количество проиндексированных чанков.
    """
    client = get_qdrant_client()
    if force:
        try:
            client.delete_collection(QDRANT_COLLECTION)
        except Exception:
            pass
    ensure_collection()
    chunks = build_chunks()
    if not chunks:
        logger.warning("Нет чанков для индексации")
        return 0
    points = []
    for i, c in enumerate(chunks):
        try:
            emb = get_embedding(c["text"])
            points.append(
                PointStruct(
                    id=i,
                    vector=emb,
                    payload={"text": c["text"], "source": c["source"]},
                )
            )
        except Exception as e:
            logger.warning("Ошибка эмбеддинга чанка %s: %s", i, e)
    if not points:
        return 0
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    logger.info("Индекс в Qdrant обновлён: %d чанков", len(points))
    return len(points)


def has_index() -> bool:
    """Проверяет, есть ли в Qdrant хотя бы один вектор в коллекции."""
    try:
        client = get_qdrant_client()
        info = client.get_collection(QDRANT_COLLECTION)
        return info.points_count > 0
    except Exception as e:
        logger.debug("has_index: %s", e)
        return False


def retrieve(
    query: str,
    top_k: int = RAG_TOP_K,
) -> str:
    """
    Поиск по запросу: эмбеддинг query, поиск в Qdrant, возврат конкатенации top_k чанков.
    """
    try:
        client = get_qdrant_client()
        if client.get_collection(QDRANT_COLLECTION).points_count == 0:
            return ""
    except Exception as e:
        logger.warning("Qdrant retrieve: %s", e)
        return ""
    try:
        q_emb = get_embedding(query)
    except Exception as e:
        logger.warning("Ошибка эмбеддинга запроса: %s", e)
        return ""
    try:
        # qdrant-client 2.x: метод search заменён на query_points
        if hasattr(client, "query_points"):
            response = client.query_points(
                collection_name=QDRANT_COLLECTION,
                query=q_emb,
                limit=top_k,
            )
            points = getattr(response, "points", None) or getattr(response, "result", None) or []
        else:
            # старый API: client.search
            points = client.search(
                collection_name=QDRANT_COLLECTION,
                query_vector=q_emb,
                limit=top_k,
            )
        texts = []
        for hit in points:
            payload = getattr(hit, "payload", None) or {}
            if isinstance(payload, dict):
                t = payload.get("text", "")
                if t:
                    texts.append(t)
        return "\n\n---\n\n".join(texts)
    except Exception as e:
        logger.warning("Ошибка поиска Qdrant: %s", e)
        return ""

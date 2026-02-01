#!/usr/bin/env python3
"""Точка входа: сборка индекса RAG в Qdrant."""
import os
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("Укажите OPENAI_API_KEY в .env")
    exit(1)

from aith_chatbot.rag import build_index

if __name__ == "__main__":
    n = build_index(force=True)
    print(f"Индекс RAG собран в Qdrant: {n} чанков")

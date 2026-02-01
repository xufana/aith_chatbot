# Чат-бот магистратур ИТМО: запуск в Docker
FROM python:3.12-slim

WORKDIR /app

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Пакет и точки входа
COPY aith_chatbot/ aith_chatbot/
COPY run_bot.py run_scraper.py run_build_rag_index.py .
COPY data/ data/

ENV PYTHONPATH=/app

CMD ["python", "-u", "run_bot.py"]

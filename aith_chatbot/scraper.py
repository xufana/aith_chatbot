"""
Парсинг страниц магистратур ИТМО: загрузка HTML, конвертация в Markdown через html2text, сохранение в data/*.md.
"""
from pathlib import Path

import html2text
import requests
from bs4 import BeautifulSoup

from .config import DATA_DIR, URL_AI, URL_AI_PRODUCT

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def fetch_page(url: str) -> str | None:
    """Загружает HTML страницы."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
        return None


def html_to_markdown(html: str) -> str:
    """
    Конвертирует HTML в Markdown с помощью html2text.
    Сохраняет структуру заголовков, списков и ссылок.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    body = soup.find("body") or soup
    html_clean = str(body) if body else html
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0
    h.ignore_emphasis = False
    return h.handle(html_clean)


def scrape_and_save_md(url: str, program_id: str) -> Path | None:
    """
    Загружает страницу, конвертирует в Markdown, сохраняет в data/{program_id}.md.
    Возвращает путь к файлу или None при ошибке.
    """
    html = fetch_page(url)
    if not html:
        return None
    md = html_to_markdown(html)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{program_id}.md"
    path.write_text(md, encoding="utf-8")
    print(f"Сохранено: {path}")
    return path


def run_scraper() -> None:
    """Запуск парсера: загрузка обеих программ, сохранение в data/*.md."""
    programs = [
        (URL_AI, "ai"),
        (URL_AI_PRODUCT, "ai_product"),
    ]
    for url, program_id in programs:
        scrape_and_save_md(url, program_id)
    print("Парсинг завершён. Файлы: data/ai.md, data/ai_product.md")

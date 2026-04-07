import io
import base64
import asyncio
from typing import List, Dict
import pandas as pd
import requests
from fastapi import APIRouter, HTTPException
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from schemas import URLRequest

router = APIRouter(prefix="/scraper", tags=["Scraper"])

# ================================
# Dynamic scraping with Playwright
# ================================
async def scrape_dynamic_site(url: str, timeout: int = 10000) -> str:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            await page.wait_for_load_state("networkidle")
            content = await page.content()
            await browser.close()
            return content
    except PlaywrightTimeoutError:
        raise HTTPException(status_code=408, detail=f"Dynamic scraping timeout for {url}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dynamic scraping error: {str(e)}")

# ================================
# Static scraping with requests
# ================================
def scrape_static_site(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Static scraping failed: {str(e)}")

# ================================
# Extract visible text from HTML
# ================================
def extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return text

# ================================
# Extract tables from HTML
# ================================
def extract_tables_from_html(html: str) -> List[pd.DataFrame]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    dfs = []
    for table in tables:
        try:
            df = pd.read_html(str(table))[0]
            if not df.empty:
                dfs.append(df)
        except Exception:
            continue
    return dfs

# ================================
# Extract all links
# ================================
def extract_links_from_html(html: str, base_url: str = "") -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a['href']
        if href.startswith("http"):
            links.append(href)
        elif base_url:
            links.append(base_url.rstrip("/") + "/" + href.lstrip("/"))
    return links

# ================================
# Smart scraper (dynamic fallback)
# ================================
async def smart_scrape(url: str) -> Dict:
    # Try dynamic scraping first
    try:
        html = await scrape_dynamic_site(url)
    except Exception:
        html = scrape_static_site(url)

    text = extract_text_from_html(html)
    tables = extract_tables_from_html(html)
    links = extract_links_from_html(html, base_url=url)

    return {
        "text": text,
        "tables": [df.to_dict(orient="records") for df in tables],
        "links": links
    }

# ================================
# FastAPI endpoint
# ================================
@router.post("/scrape-url")
async def scrape_url(req: URLRequest):
    try:
        result = await smart_scrape(req.url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

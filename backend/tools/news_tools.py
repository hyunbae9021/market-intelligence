"""
뉴스 & 미디어 데이터 수집 도구
- Google News RSS (무료, 키 불필요)
- CryptoPanic API (무료 티어)
- cryptocurrency.cv (무료, 키 불필요)
"""
from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx


TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def fetch_google_news_rss(query: str, lang: str = "ko", count: int = 20) -> List[Dict]:
    """Google News RSS로 뉴스 수집 (API 키 불필요)"""
    encoded_query = quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang}&gl=KR&ceid=KR:ko"

    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                return items

            root = ET.fromstring(resp.text)
            channel = root.find("channel")
            if channel is None:
                return items

            for item in channel.findall("item")[:count]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                description = item.findtext("description", "")

                items.append({
                    "title": title,
                    "url": link,
                    "source": "Google News RSS",
                    "published_at": pub_date,
                    "summary": description[:300] if description else "",
                    "query": query,
                })
    except Exception as e:
        items.append({"error": str(e), "source": "Google News RSS"})

    return items


async def fetch_cryptopanic_news(
    currencies: str = "BTC,ETH",
    kind: str = "news",
    count: int = 20,
    api_key: Optional[str] = None,
) -> List[Dict]:
    """CryptoPanic API 뉴스 수집 (무료 티어 가능)"""
    base_url = "https://cryptopanic.com/api/v1/posts/"
    params: Dict[str, Any] = {
        "currencies": currencies,
        "kind": kind,
        "public": "true",
    }
    if api_key:
        params["auth_token"] = api_key

    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(base_url, params=params)
            if resp.status_code != 200:
                return items

            data = resp.json()
            for post in data.get("results", [])[:count]:
                items.append({
                    "title": post.get("title", ""),
                    "url": post.get("url", ""),
                    "source": post.get("source", {}).get("title", "CryptoPanic"),
                    "published_at": post.get("published_at", ""),
                    "summary": post.get("title", ""),
                    "sentiment": post.get("votes", {}).get("positive", 0) - post.get("votes", {}).get("negative", 0),
                    "category": "crypto",
                })
    except Exception as e:
        items.append({"error": str(e), "source": "CryptoPanic"})

    return items


async def fetch_sec_edgar_rss(company_name: str = "", form_type: str = "") -> List[Dict]:
    """SEC EDGAR RSS 피드 (무료, 키 불필요)"""
    if company_name:
        url = f"https://efts.sec.gov/LATEST/search-index?q={quote(company_name)}&dateRange=custom&startdt=2024-01-01&forms={form_type}&hits.hits.total.value=true"
    else:
        url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=20&search_text=&output=atom"

    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "MarketIntelligence research@company.com"})
            if resp.status_code != 200:
                return items

            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns)[:10]:
                title = entry.findtext("atom:title", "", ns)
                link_el = entry.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                updated = entry.findtext("atom:updated", "", ns)
                summary = entry.findtext("atom:summary", "", ns)

                items.append({
                    "title": title,
                    "url": link,
                    "source": "SEC EDGAR",
                    "published_at": updated,
                    "summary": summary[:300],
                    "category": "regulatory",
                })
    except Exception as e:
        items.append({"error": str(e), "source": "SEC EDGAR"})

    return items


async def gather_news(
    topic: str,
    crypto_currencies: str = "BTC,ETH",
    cryptopanic_key: Optional[str] = None,
) -> Dict[str, Any]:
    """여러 뉴스 소스를 병렬로 수집"""
    results = await asyncio.gather(
        fetch_google_news_rss(topic, lang="ko"),
        fetch_google_news_rss(topic, lang="en"),
        fetch_cryptopanic_news(crypto_currencies, api_key=cryptopanic_key),
        fetch_sec_edgar_rss(),
        return_exceptions=True,
    )

    return {
        "google_news_ko": results[0] if not isinstance(results[0], Exception) else [],
        "google_news_en": results[1] if not isinstance(results[1], Exception) else [],
        "cryptopanic": results[2] if not isinstance(results[2], Exception) else [],
        "sec_edgar": results[3] if not isinstance(results[3], Exception) else [],
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
    }

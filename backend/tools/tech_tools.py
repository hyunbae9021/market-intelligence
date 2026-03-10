"""
기술 트렌드 데이터 수집 도구
- GitHub API (오픈소스 트렌드, 무료)
- ArXiv API (AI/기술 논문, 무료 키 불필요)
- HuggingFace API (AI 모델 트렌드, 무료)
"""
from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx


TIMEOUT = httpx.Timeout(15.0, connect=5.0)


async def fetch_arxiv_papers(
    query: str,
    max_results: int = 10,
    category: str = "cs.AI",
) -> List[Dict]:
    """ArXiv API - AI/기술 최신 논문 (완전 무료, 키 불필요)"""
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"cat:{category} AND all:{quote(query)}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return items

            root = ET.fromstring(resp.text)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }

            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", "", ns).strip()
                summary = entry.findtext("atom:summary", "", ns).strip()
                published = entry.findtext("atom:published", "", ns)
                link_el = entry.find("atom:id", ns)
                link = link_el.text if link_el is not None else ""

                authors = [
                    a.findtext("atom:name", "", ns)
                    for a in entry.findall("atom:author", ns)
                ]

                items.append({
                    "title": title,
                    "summary": summary[:500],
                    "authors": authors[:3],
                    "published_at": published,
                    "url": link,
                    "source": f"ArXiv ({category})",
                })
    except Exception as e:
        items.append({"error": str(e), "source": "ArXiv API"})

    return items


async def fetch_github_trending(
    language: str = "",
    since: str = "weekly",
    github_token: Optional[str] = None,
) -> List[Dict]:
    """GitHub 트렌딩 레포지토리"""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    # GitHub 공식 트렌딩 API는 없으므로 검색 API 활용
    query = "stars:>1000"
    if language:
        query += f" language:{language}"

    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as client:
            resp = await client.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 10,
                },
            )
            if resp.status_code == 200:
                for repo in resp.json().get("items", []):
                    items.append({
                        "name": repo.get("full_name", ""),
                        "description": repo.get("description", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "language": repo.get("language", ""),
                        "topics": repo.get("topics", []),
                        "url": repo.get("html_url", ""),
                        "created_at": repo.get("created_at", ""),
                        "source": "GitHub Trending",
                    })
    except Exception as e:
        items.append({"error": str(e), "source": "GitHub"})

    return items


async def fetch_huggingface_models(
    task: str = "text-generation",
    limit: int = 10,
) -> List[Dict]:
    """HuggingFace 인기 AI 모델 (무료 API)"""
    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                "https://huggingface.co/api/models",
                params={
                    "pipeline_tag": task,
                    "sort": "downloads",
                    "direction": -1,
                    "limit": limit,
                },
            )
            if resp.status_code == 200:
                for model in resp.json():
                    items.append({
                        "name": model.get("modelId", ""),
                        "author": model.get("author", ""),
                        "downloads": model.get("downloads", 0),
                        "likes": model.get("likes", 0),
                        "task": task,
                        "tags": model.get("tags", [])[:5],
                        "source": "HuggingFace",
                    })
    except Exception as e:
        items.append({"error": str(e), "source": "HuggingFace"})

    return items


async def gather_tech_data(
    topics: List[str],
    github_token: Optional[str] = None,
) -> Dict[str, Any]:
    """기술 트렌드 데이터 병렬 수집"""
    arxiv_tasks = [fetch_arxiv_papers(topic, max_results=5) for topic in topics[:3]]
    github_tasks = [
        fetch_github_trending(language="Python", github_token=github_token),
        fetch_github_trending(language="TypeScript", github_token=github_token),
    ]
    hf_tasks = [
        fetch_huggingface_models("text-generation", limit=5),
        fetch_huggingface_models("text-classification", limit=5),
    ]

    all_results = await asyncio.gather(
        *arxiv_tasks, *github_tasks, *hf_tasks,
        return_exceptions=True,
    )

    arxiv_data = []
    for r in all_results[:len(arxiv_tasks)]:
        if not isinstance(r, Exception):
            arxiv_data.extend(r)

    github_data = []
    for r in all_results[len(arxiv_tasks):len(arxiv_tasks) + len(github_tasks)]:
        if not isinstance(r, Exception):
            github_data.extend(r)

    hf_data = []
    for r in all_results[len(arxiv_tasks) + len(github_tasks):]:
        if not isinstance(r, Exception):
            hf_data.extend(r)

    return {
        "arxiv_papers": arxiv_data,
        "github_trending": github_data,
        "huggingface_models": hf_data,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "topics": topics,
    }

"""
기업/스타트업 정보 수집 도구
- DART OpenAPI (한국 금감원, 무료 - API 키 필요)
- GitHub API (기술 기업 오픈소스 활동, 무료)
- CoinGecko 거래소 데이터
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx


TIMEOUT = httpx.Timeout(15.0, connect=5.0)
DART_BASE = "https://opendart.fss.or.kr/api"
GITHUB_BASE = "https://api.github.com"


async def fetch_dart_company_info(
    company_name: str,
    dart_api_key: str,
) -> List[Dict]:
    """DART OpenAPI - 한국 기업 공시 정보 수집"""
    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # 기업 코드 검색
            search_resp = await client.get(
                f"{DART_BASE}/company.json",
                params={
                    "crtfc_key": dart_api_key,
                    "corp_name": company_name,
                    "page_count": 10,
                },
            )
            if search_resp.status_code != 200:
                return items

            data = search_resp.json()
            if data.get("status") != "000":
                return items

            for corp in (data.get("list") or [])[:5]:
                corp_code = corp.get("corp_code", "")
                items.append({
                    "name": corp.get("corp_name", ""),
                    "corp_code": corp_code,
                    "stock_code": corp.get("stock_code", ""),
                    "ceo": corp.get("ceo_nm", ""),
                    "country": "KR",
                    "industry": corp.get("induty_code", ""),
                    "address": corp.get("adres", ""),
                    "website": corp.get("hm_url", ""),
                    "source": "DART OpenAPI",
                })
    except Exception as e:
        items.append({"error": str(e), "source": "DART OpenAPI"})

    return items


async def fetch_dart_recent_disclosures(
    corp_code: str,
    dart_api_key: str,
    bgn_de: str = "20240101",
) -> List[Dict]:
    """DART - 최근 공시 목록"""
    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{DART_BASE}/list.json",
                params={
                    "crtfc_key": dart_api_key,
                    "corp_code": corp_code,
                    "bgn_de": bgn_de,
                    "sort": "date",
                    "sort_mth": "desc",
                    "page_count": 20,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in (data.get("list") or [])[:10]:
                    items.append({
                        "title": item.get("report_nm", ""),
                        "date": item.get("rcept_dt", ""),
                        "type": item.get("pblntf_ty", ""),
                        "source": "DART 공시",
                    })
    except Exception as e:
        items.append({"error": str(e), "source": "DART 공시"})

    return items


async def fetch_github_org_info(org_name: str, github_token: Optional[str] = None) -> Dict:
    """GitHub 조직 정보 (기술 기업 오픈소스 활동)"""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as client:
            org_resp = await client.get(f"{GITHUB_BASE}/orgs/{org_name}")
            if org_resp.status_code != 200:
                return {}

            org = org_resp.json()

            # 인기 레포지토리
            repos_resp = await client.get(
                f"{GITHUB_BASE}/orgs/{org_name}/repos",
                params={"sort": "stars", "per_page": 5},
            )
            repos = repos_resp.json() if repos_resp.status_code == 200 else []

            return {
                "name": org.get("name", org_name),
                "description": org.get("description", ""),
                "website": org.get("blog", ""),
                "public_repos": org.get("public_repos", 0),
                "followers": org.get("followers", 0),
                "created_at": org.get("created_at", ""),
                "top_repos": [
                    {
                        "name": r.get("name", ""),
                        "stars": r.get("stargazers_count", 0),
                        "language": r.get("language", ""),
                        "description": r.get("description", ""),
                    }
                    for r in (repos if isinstance(repos, list) else [])[:5]
                ],
                "source": "GitHub API",
            }
    except Exception as e:
        return {"error": str(e), "source": "GitHub API"}


async def fetch_coingecko_exchanges(api_key: Optional[str] = None) -> List[Dict]:
    """CoinGecko 거래소 정보 (경쟁사 분석용)"""
    headers = {}
    if api_key:
        headers["x-cg-demo-api-key"] = api_key

    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/exchanges",
                params={"per_page": 20, "page": 1},
            )
            if resp.status_code == 200:
                for ex in resp.json():
                    items.append({
                        "name": ex.get("name", ""),
                        "country": ex.get("country", ""),
                        "volume_24h_btc": ex.get("trade_volume_24h_btc", 0),
                        "trust_score": ex.get("trust_score", 0),
                        "year_established": ex.get("year_established", ""),
                        "url": ex.get("url", ""),
                        "source": "CoinGecko Exchanges",
                    })
    except Exception as e:
        items.append({"error": str(e), "source": "CoinGecko Exchanges"})

    return items


async def gather_company_data(
    target_companies: List[str],
    dart_api_key: Optional[str] = None,
    github_token: Optional[str] = None,
    coingecko_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """기업 데이터 수집"""
    tasks = [fetch_coingecko_exchanges(api_key=coingecko_api_key)]

    # DART 데이터 (한국 기업)
    dart_results = []
    if dart_api_key and target_companies:
        for company in target_companies[:3]:
            dart_results.append(
                fetch_dart_company_info(company, dart_api_key)
            )

    # GitHub 데이터
    github_results = []
    tech_orgs = ["coinbase", "binance-chain", "ethereum", "solana-labs"]
    for org in tech_orgs[:2]:
        github_results.append(fetch_github_org_info(org, github_token))

    all_results = await asyncio.gather(
        *tasks, *dart_results, *github_results,
        return_exceptions=True,
    )

    exchanges = all_results[0] if not isinstance(all_results[0], Exception) else []
    dart_data = []
    for r in all_results[1:1 + len(dart_results)]:
        if not isinstance(r, Exception):
            dart_data.extend(r)
    github_data = []
    for r in all_results[1 + len(dart_results):]:
        if not isinstance(r, Exception):
            github_data.append(r)

    return {
        "exchanges": exchanges,
        "dart_companies": dart_data,
        "github_orgs": github_data,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }

"""
시장/산업 데이터 수집 도구
- CoinGecko API (무료 Demo 티어, 30 calls/min)
- DefiLlama API (완전 무료, 키 불필요)
- DexScreener API (완전 무료, 키 불필요)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx


TIMEOUT = httpx.Timeout(15.0, connect=5.0)
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEFILLAMA_BASE = "https://api.llama.fi"


async def fetch_coingecko_market_data(
    vs_currency: str = "usd",
    category: Optional[str] = None,
    per_page: int = 30,
    api_key: Optional[str] = None,
) -> List[Dict]:
    """CoinGecko 시장 데이터 수집"""
    url = f"{COINGECKO_BASE}/coins/markets"
    params: Dict[str, Any] = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h,7d",
    }
    if category:
        params["category"] = category

    headers = {}
    if api_key:
        headers["x-cg-demo-api-key"] = api_key

    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                for coin in resp.json():
                    items.append({
                        "name": coin.get("name", ""),
                        "symbol": coin.get("symbol", "").upper(),
                        "market_cap_usd": coin.get("market_cap", 0),
                        "price_usd": coin.get("current_price", 0),
                        "volume_24h_usd": coin.get("total_volume", 0),
                        "price_change_24h_pct": coin.get("price_change_percentage_24h", 0),
                        "price_change_7d_pct": coin.get("price_change_percentage_7d_in_currency", 0),
                        "source": "CoinGecko",
                    })
    except Exception as e:
        items.append({"error": str(e), "source": "CoinGecko"})

    return items


async def fetch_coingecko_global() -> Dict:
    """CoinGecko 글로벌 시장 통계"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{COINGECKO_BASE}/global")
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return {
                    "total_market_cap_usd": data.get("total_market_cap", {}).get("usd", 0),
                    "total_volume_24h_usd": data.get("total_volume", {}).get("usd", 0),
                    "btc_dominance_pct": data.get("market_cap_percentage", {}).get("btc", 0),
                    "eth_dominance_pct": data.get("market_cap_percentage", {}).get("eth", 0),
                    "active_cryptocurrencies": data.get("active_cryptocurrencies", 0),
                    "market_cap_change_24h_pct": data.get("market_cap_change_percentage_24h_usd", 0),
                    "source": "CoinGecko Global",
                }
    except Exception as e:
        return {"error": str(e), "source": "CoinGecko Global"}
    return {}


async def fetch_defillama_protocols(limit: int = 20) -> List[Dict]:
    """DefiLlama DeFi 프로토콜 TVL 데이터 (완전 무료)"""
    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{DEFILLAMA_BASE}/protocols")
            if resp.status_code == 200:
                protocols = resp.json()[:limit]
                for p in protocols:
                    items.append({
                        "name": p.get("name", ""),
                        "category": p.get("category", ""),
                        "chain": p.get("chain", ""),
                        "tvl_usd": p.get("tvl", 0),
                        "change_1h_pct": p.get("change_1h", 0),
                        "change_24h_pct": p.get("change_1d", 0),
                        "change_7d_pct": p.get("change_7d", 0),
                        "source": "DefiLlama",
                    })
    except Exception as e:
        items.append({"error": str(e), "source": "DefiLlama"})

    return items


async def fetch_defillama_chains() -> List[Dict]:
    """DefiLlama 체인별 TVL 데이터"""
    items = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{DEFILLAMA_BASE}/v2/chains")
            if resp.status_code == 200:
                for chain in resp.json()[:20]:
                    items.append({
                        "name": chain.get("name", ""),
                        "tvl_usd": chain.get("tvl", 0),
                        "source": "DefiLlama Chains",
                    })
    except Exception as e:
        items.append({"error": str(e), "source": "DefiLlama Chains"})

    return items


async def fetch_defillama_stablecoins() -> Dict:
    """DefiLlama 스테이블코인 데이터"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get("https://stablecoins.llama.fi/stablecoins?includePrices=true")
            if resp.status_code == 200:
                data = resp.json()
                peggedAssets = data.get("peggedAssets", [])[:10]
                return {
                    "total_stablecoin_market_cap_usd": data.get("totalCirculatingUSD", {}).get("peggedUSD", 0),
                    "top_stablecoins": [
                        {
                            "name": s.get("name", ""),
                            "symbol": s.get("symbol", ""),
                            "circulating_usd": s.get("circulating", {}).get("peggedUSD", 0),
                            "source": "DefiLlama Stablecoins",
                        }
                        for s in peggedAssets
                    ],
                    "source": "DefiLlama Stablecoins",
                }
    except Exception as e:
        return {"error": str(e), "source": "DefiLlama Stablecoins"}
    return {}


async def gather_market_data(
    coingecko_api_key: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """시장 데이터 병렬 수집"""
    results = await asyncio.gather(
        fetch_coingecko_market_data(per_page=30, api_key=coingecko_api_key, category=category),
        fetch_coingecko_global(),
        fetch_defillama_protocols(limit=20),
        fetch_defillama_chains(),
        fetch_defillama_stablecoins(),
        return_exceptions=True,
    )

    return {
        "coingecko_markets": results[0] if not isinstance(results[0], Exception) else [],
        "coingecko_global": results[1] if not isinstance(results[1], Exception) else {},
        "defillama_protocols": results[2] if not isinstance(results[2], Exception) else [],
        "defillama_chains": results[3] if not isinstance(results[3], Exception) else [],
        "defillama_stablecoins": results[4] if not isinstance(results[4], Exception) else {},
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }

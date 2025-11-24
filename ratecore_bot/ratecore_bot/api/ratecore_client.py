from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class RateCoreClient:
    """Async HTTP client for RateCore API."""

    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        async with self._lock:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_price(self, symbol: str) -> dict[str, Any]:
        session = await self._get_session()
        url = f"{self._base_url}/api/v1/price/{symbol}"
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_prices_batch(self, symbols: list[str]) -> list[dict[str, Any]]:
        """
        Call POST /api/v1/prices/batch and return list of price dicts.
        """
        session = await self._get_session()
        url = f"{self._base_url}/api/v1/prices/batch"
        payload = {"symbols": symbols}
        async with session.post(url, json=payload) as resp:
            resp.raise_for_status()
            data = await resp.json()
            items = data.get("items") or data.get("Items") or data
            return items if isinstance(items, list) else []

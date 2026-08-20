import aiohttp
import asyncio
import logging
import time
from typing import List, Optional
from sentiment.nlp_analyzer import TuringNewsItem, TuringSentimentAnalyzer

logger = logging.getLogger("CryptoPanicStreamerTuring")

class TuringNewsStreamer:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.analyzer = TuringSentimentAnalyzer()
        self.seen_titles = set()

    async def fetch_latest_news(self) -> List[TuringNewsItem]:
        url = "https://cryptopanic.com/api/v1/posts/?public=true"
        if self.api_key:
            url += f"&auth_token={self.api_key}"

        new_items = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        for r in results[:10]:
                            title = r.get("title", "")
                            if title and title not in self.seen_titles:
                                self.seen_titles.add(title)
                                processed = self.analyzer.analyze_headline(title)
                                new_items.append(processed)
        except Exception:
            pass

        return new_items

import logging
import math
import time
from typing import List, Dict, Tuple
from dataclasses import dataclass

logger = logging.getLogger("NLPAnalyzerTuring")

@dataclass
class TuringNewsItem:
    title: str
    published_at: float
    sentiment_score: float
    confidence: float
    source: str

class TuringSentimentAnalyzer:
    def __init__(self, half_life_minutes: float = 45.0):
        self.half_life_seconds = half_life_minutes * 60.0
        self.decay_constant = math.log(2) / self.half_life_seconds

        self.bullish_keywords = [
            "surge", "rally", "soar", "pump", "breakout", "bullish", "all-time high", "ath",
            "etf approval", "institutional buy", "whale inflow", "partnership", "adoption",
            "upgrade", "mainnet", "burn", "deflationary", "expansion"
        ]
        self.bearish_keywords = [
            "dump", "crash", "plunge", "bearish", "hack", "exploit", "sec lawsuit", "ban",
            "fud", "insolvency", "bankruptcy", "liquidation", "outflow", "rugpull", "scam"
        ]
        self.black_swan_keywords = [
            "emergency", "halted", "collapse", "war", "sec ban", "catastrophe", "seized"
        ]

    def analyze_headline(self, title: str) -> TuringNewsItem:
        text = title.lower()
        bull_hits = sum(1 for kw in self.bullish_keywords if kw in text)
        bear_hits = sum(1 for kw in self.bearish_keywords if kw in text)

        total_hits = bull_hits + bear_hits
        if total_hits > 0:
            score = (bull_hits - bear_hits) / float(total_hits)
            confidence = min(0.95, 0.40 + (0.15 * total_hits))
        else:
            score = 0.0
            confidence = 0.20

        return TuringNewsItem(
            title=title,
            published_at=time.time(),
            sentiment_score=score,
            confidence=confidence,
            source="CryptoPanic"
        )

    def calculate_decayed_sentiment(self, news_history: List[TuringNewsItem]) -> Tuple[float, float, bool]:
        if not news_history:
            return 0.0, 0.0, False

        now = time.time()
        weighted_score_sum = 0.0
        total_weight = 0.0
        confidence_sum = 0.0
        has_black_swan = False

        for item in news_history:
            age = max(0.0, now - item.published_at)
            decay_factor = math.exp(-self.decay_constant * age)
            weight = decay_factor * item.confidence

            weighted_score_sum += item.sentiment_score * weight
            total_weight += weight
            confidence_sum += item.confidence * decay_factor

            for bsk in self.black_swan_keywords:
                if bsk in item.title.lower():
                    has_black_swan = True
                    break

        decayed_score = weighted_score_sum / total_weight if total_weight > 0 else 0.0
        avg_confidence = confidence_sum / len(news_history) if news_history else 0.0

        return float(decayed_score), float(avg_confidence), has_black_swan

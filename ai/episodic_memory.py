import json
import os
import time
import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("EpisodicMemoryEngineTuring")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MEMORY_FILE = os.path.join(DATA_DIR, "episodic_memory.json")

@dataclass
class MarketVector:
    symbol: str
    action: str  # "BUY" o "SELL"
    trend_direction: float  # +1.0 o -1.0
    volatility_atr_pct: float
    order_book_imbalance: float
    volume_delta: float
    entropy: float
    ising_magnetization: float
    sentiment_score: float
    conviction: float

@dataclass
class TradeMemoryEpisode:
    episode_id: str
    symbol: str
    action: str
    entry_price: float
    exit_price: float
    net_pnl: float
    win: bool
    opened_at: float
    closed_at: float
    vector: Dict[str, float]
    reflection_note: str

class EpisodicMemoryEngine:
    def __init__(self, max_episodes: int = 500, similarity_threshold: float = 0.72):
        self.max_episodes = max_episodes
        self.similarity_threshold = similarity_threshold
        self.episodes: List[TradeMemoryEpisode] = []
        self._load_memory()

    def _ensure_dir(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)

    def _load_memory(self):
        self._ensure_dir()
        if not os.path.exists(MEMORY_FILE):
            return
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.episodes = [TradeMemoryEpisode(**item) for item in data]
                logger.info(f"🧠 [MEMORIA TURING]: Cargados {len(self.episodes)} episodios históricos desde disco.")
        except Exception as e:
            logger.error(f"Error cargando memoria episódica en TURING: {e}")

    def _save_memory(self):
        self._ensure_dir()
        try:
            temp_file = MEMORY_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump([asdict(e) for e in self.episodes[-self.max_episodes:]], f, indent=2)
            if os.path.exists(MEMORY_FILE):
                os.remove(MEMORY_FILE)
            os.rename(temp_file, MEMORY_FILE)
        except Exception as e:
            logger.error(f"Error guardando memoria episódica en TURING: {e}")

    def _vector_to_array(self, vec: MarketVector) -> np.ndarray:
        return np.array([
            vec.trend_direction,
            vec.volatility_atr_pct * 100.0,
            vec.order_book_imbalance,
            vec.volume_delta,
            vec.entropy,
            vec.ising_magnetization,
            vec.sentiment_score
        ], dtype=float)

    def _dict_to_array(self, d: Dict[str, float]) -> np.ndarray:
        return np.array([
            d.get("trend_direction", 0.0),
            d.get("volatility_atr_pct", 0.01) * 100.0,
            d.get("order_book_imbalance", 0.0),
            d.get("volume_delta", 0.0),
            d.get("entropy", 0.30),
            d.get("ising_magnetization", 0.0),
            d.get("sentiment_score", 0.0)
        ], dtype=float)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def query_past_experience(self, current_vector: MarketVector) -> Tuple[float, float, str]:
        if not self.episodes:
            return 1.0, 0.50, "Experiencia inicial: Sin precedentes directos."

        target_arr = self._vector_to_array(current_vector)
        matches = []

        for ep in self.episodes:
            if ep.symbol != current_vector.symbol or ep.action != current_vector.action:
                continue
            ep_arr = self._dict_to_array(ep.vector)
            sim = self._cosine_similarity(target_arr, ep_arr)
            if sim >= self.similarity_threshold:
                matches.append((sim, ep))

        if not matches:
            return 1.0, 0.50, "Patrón de mercado novedoso: Ejecución estándar."

        wins = sum(1 for m in matches if m[1].win)
        losses = sum(1 for m in matches if not m[1].win)
        win_rate = wins / float(len(matches))

        if losses >= 2 and win_rate < 0.35:
            multiplier = 0.0  # VETO TOTAL
            insight = f"🛑 VETO POR MEMORIA TURING: En {len(matches)} situaciones idénticas ({losses} pérdidas), el resultado fue adverso."
        elif win_rate >= 0.70:
            multiplier = 1.35  # IMPULSO AGRESIVO TURING
            insight = f"💎 EXPERIENCIA GANADORA ({win_rate:.0%} Win Rate en {len(matches)} episodios). Potenciando tamaño y apalancamiento."
        else:
            multiplier = 1.0
            insight = f"Experiencia balanceada ({wins}W / {losses}L)."

        return multiplier, win_rate, insight

    def record_completed_trade(
        self,
        pos_id: str,
        vector: MarketVector,
        entry_price: float,
        exit_price: float,
        net_pnl: float,
        opened_at: float
    ):
        win = net_pnl > 0
        if win:
            note = f"🏆 Trade exitoso en {vector.symbol} ({vector.action}). PnL: +${net_pnl:.2f}"
        else:
            note = f"⚠️ Pérdida en {vector.symbol} ({vector.action}). PnL: -${abs(net_pnl):.2f}"

        episode = TradeMemoryEpisode(
            episode_id=pos_id,
            symbol=vector.symbol,
            action=vector.action,
            entry_price=entry_price,
            exit_price=exit_price,
            net_pnl=net_pnl,
            win=win,
            opened_at=opened_at,
            closed_at=time.time(),
            vector=asdict(vector),
            reflection_note=note
        )
        self.episodes.append(episode)
        self._save_memory()
        logger.info(f"🧠 [MEMORIA TURING GUARDADA]: {note}")
